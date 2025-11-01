"""
Filesystem Journaling Crash Test Tool

A tool to evaluate filesystem journaling effectiveness through simulated crash scenarios.
Tests filesystem data integrity by interrupting file operations and verifying recovery.
"""

import os
import time
import shutil
import hashlib
import platform
import datetime
import argparse
from pathlib import Path
import threading
import sys


class JournalingRealTest:
    """Main class for filesystem journaling crash testing"""
    
    def __init__(self, fs_type, size_gb=2, results_dir="fs_test_results"):
        """
        Initialize the journaling test environment.
        
        Args:
            fs_type (str): Filesystem type (e.g., 'NTFS', 'ext4', 'XFS')
            size_gb (int): Size of test file in GB
            results_dir (str): Directory to store test results
        """
        # Use current directory instead of trying to find Desktop
        self.current_dir = Path.cwd()
        
        print(f"Current directory: {self.current_dir}")
        
        self.test_dir = self.current_dir
        self.fs_type = fs_type
        self.size_gb = size_gb
        self.results_dir = self.current_dir / results_dir
        self.results_dir.mkdir(exist_ok=True)
        
        # Add option to control artificial delay
        self.use_delay = True
        
        # Create necessary directories
        self.source_dir = self.test_dir / "source_test"
        self.dest_dir = self.test_dir / "destination_test"
        
        self.source_dir.mkdir(exist_ok=True)
        self.dest_dir.mkdir(exist_ok=True)
        
        # Large file name
        self.large_file = self.source_dir / f"large_file_{size_gb}gb.dat"
        self.dest_file = self.dest_dir / f"large_file_{size_gb}gb.dat"
        
        print(f"Journaling test for {fs_type}")
        print(f"Using file size: {size_gb}GB")
        print(f"Source directory: {self.source_dir}")
        print(f"Destination directory: {self.dest_dir}")
        print(f"Source file: {self.large_file}")
    
    def create_large_file(self):
        """
        Create a large file of specified size for testing.
        
        Returns:
            bool: True if successful, False otherwise
        """
        print(f"Creating {self.size_gb}GB file...")
        
        # File size in bytes
        file_size = int(self.size_gb * 1024 * 1024 * 1024)
        
        # Check if file already exists
        if self.large_file.exists():
            current_size = self.large_file.stat().st_size
            if current_size == file_size:
                print(f"File already exists with correct size ({self.size_gb}GB)")
                return True
            else:
                print(f"File exists with different size. Recreating...")
                os.remove(self.large_file)
        
        # Create test file
        chunk_size = 10 * 1024 * 1024  # 10MB chunks
        chunk = os.urandom(chunk_size)  # Random data
        
        try:
            with open(self.large_file, 'wb') as f:
                remaining = file_size
                last_progress = -1
                
                while remaining > 0:
                    write_size = min(chunk_size, remaining)
                    f.write(chunk[:write_size])
                    remaining -= write_size
                    
                    # Show progress (only update when changed)
                    progress = int(100 * (file_size - remaining) / file_size)
                    if progress != last_progress:
                        print(f"Progress: {progress}%", end='\r')
                        last_progress = progress
                
                # Ensure data is written to disk
                f.flush()
                os.fsync(f.fileno())
            
            print(f"\nFile created successfully: {self.large_file}")
            return True
            
        except Exception as e:
            print(f"Error creating file: {str(e)}")
            return False
    
    def calculate_checksum(self, file_path):
        """
        Calculate MD5 checksum of a file.
        
        Args:
            file_path (Path): Path to the file
            
        Returns:
            str: MD5 checksum or None if error
        """
        print(f"Calculating checksum for: {file_path}")
        try:
            md5 = hashlib.md5()
            file_size = os.path.getsize(file_path)
            processed = 0
            last_progress = -1
            
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096 * 1024), b''):  # 4MB chunks
                    md5.update(chunk)
                    processed += len(chunk)
                    
                    # Show progress for large files
                    if file_size > 100 * 1024 * 1024:  # Only for files > 100MB
                        progress = int(100 * processed / file_size)
                        if progress != last_progress:
                            print(f"Checksum progress: {progress}%", end='\r')
                            last_progress = progress
            
            checksum = md5.hexdigest()
            print(f"\nChecksum: {checksum}")
            return checksum
        except Exception as e:
            print(f"Error calculating checksum: {str(e)}")
            return None
    
    def copy_file_with_progress(self):
        """
        Copy file with progress monitoring and crash point detection.
        
        Returns:
            bool: True if copy initiated successfully, False otherwise
        """
        if not self.large_file.exists():
            print(f"Source file doesn't exist: {self.large_file}")
            print("Please create file first using --create with the same --size parameter")
            return False
        
        if self.dest_file.exists():
            print(f"Destination file already exists. Removing...")
            os.remove(self.dest_file)
        
        # Save original file checksum
        original_checksum = self.calculate_checksum(self.large_file)
        checksum_file = self.source_dir / "original_checksum.txt"
        with open(checksum_file, 'w') as f:
            f.write(original_checksum)
            f.flush()
            os.fsync(f.fileno())
        
        print("\n" + "="*60)
        print(" FILE COPY CRASH TEST ".center(60, "="))
        print("="*60)
        print("\nThe file will be copied, and at 40-60% progress")
        print("you will be asked to forcibly shut down the computer.")
        print("\nIMPORTANT: Use forced shutdown (hold power button)")
        print("           Do NOT use normal shutdown!")
        
        # Print delay status
        if self.use_delay:
            print("\n✓ Using artificial delay for easier testing.")
        else:
            print("\n⚠ Running at full speed (no artificial delay).")
            print("  Shutdown window will be very short!")
        
        print("\n" + "="*60)
        input("Press Enter when ready to start...")
        
        # Start copy in separate thread
        self.copy_thread = threading.Thread(target=self._copy_file_thread)
        self.copy_thread.daemon = True
        self.shutdown_prompted = False
        self.copy_thread.start()
        
        # Wait for progress to reach shutdown point
        file_size = os.path.getsize(self.large_file)
        
        while self.copy_thread.is_alive():
            if self.dest_file.exists():
                try:
                    copied_size = os.path.getsize(self.dest_file)
                    progress = 100 * copied_size / file_size
                    print(f"Progress: {progress:.1f}%", end='\r')
                    
                    # When progress is 40-60%, ask user to shutdown
                    if 40 <= progress <= 60 and not self.shutdown_prompted:
                        self.shutdown_prompted = True
                        print("\n" + "="*60)
                        print(" CRASH POINT REACHED! ".center(60, "="))
                        print("="*60)
                        print("\n⚠️  SHUT DOWN YOUR COMPUTER NOW! ⚠️")
                        print("\n   Hold the power button until computer turns off")
                        print("   OR disconnect the power cable")
                        print("\n   You have 30 seconds before copy continues...")
                        print("\n" + "="*60 + "\n")
                        
                        # Wait for 30 seconds to give user time to shutdown
                        for i in range(30, 0, -1):
                            print(f"⚠️  SHUTDOWN NOW! {i} seconds remaining...".ljust(50), end='\r')
                            time.sleep(1)
                        
                        print("\n\nShutdown window passed. Copy continuing...")
                        
                except Exception as e:
                    pass
                    
            time.sleep(0.5)
        
        print("\n\nFile copy completed.")
        print("If you shut down during the crash window, reboot and run:")
        print(f"  python {sys.argv[0]} --type {self.fs_type} --size {self.size_gb} --verify")
        return True
    
    def _copy_file_thread(self):
        """Thread for file copying with optional deliberate slowdown"""
        try:
            with open(self.large_file, 'rb') as src:
                with open(self.dest_file, 'wb') as dst:
                    while True:
                        buf = src.read(1024 * 1024)  # Read 1MB at a time
                        if not buf:
                            break
                        dst.write(buf)
                        dst.flush()  # Ensure write to disk
                        
                        # Add deliberate slowdown only if requested
                        if self.use_delay:
                            time.sleep(0.2)  # 200ms delay per MB
                        
        except Exception as e:
            print(f"\nError during copy: {str(e)}")
    
    def verify_after_crash(self):
        """
        Verify file status after restart and evaluate journaling effectiveness.
        
        Returns:
            dict: Results dictionary with file integrity information
        """
        print("\n" + "="*60)
        print(" VERIFYING FILES AFTER CRASH ".center(60, "="))
        print("="*60 + "\n")
        
        # Auto-detect file size if not specified
        if not self.large_file.exists() and not self.dest_file.exists():
            print("Neither source nor destination file exists.")
            
            # Try to find files in the directories
            source_files = list(self.source_dir.glob("large_file_*gb.dat"))
            if source_files:
                print(f"Found file: {source_files[0].name}")
                size_str = source_files[0].name.split('_')[2].split('gb')[0]
                try:
                    self.size_gb = int(size_str)
                    self.large_file = self.source_dir / f"large_file_{self.size_gb}gb.dat"
                    self.dest_file = self.dest_dir / f"large_file_{self.size_gb}gb.dat"
                    print(f"Auto-detected file size: {self.size_gb}GB")
                except Exception as e:
                    print(f"Could not auto-detect file size: {e}")
                    return False
        
        # Check for source checksum file
        checksum_file = self.source_dir / "original_checksum.txt"
        if not checksum_file.exists():
            print("❌ Checksum file not found. Must run --create and --test first.")
            return False
        
        # Read original checksum
        with open(checksum_file, 'r') as f:
            original_checksum = f.read().strip()
        
        results = {
            "source_exists": self.large_file.exists(),
            "destination_exists": self.dest_file.exists(),
            "source_intact": False,
            "destination_intact": False
        }
        
        # Check source file integrity
        if results["source_exists"]:
            print("Checking source file integrity...")
            current_checksum = self.calculate_checksum(self.large_file)
            results["source_intact"] = (current_checksum == original_checksum)
            
            if results["source_intact"]:
                print("✓ Source file is completely intact!")
            else:
                print("✗ Source file exists but is corrupted!")
        else:
            print("✗ Source file does not exist!")
        
        # Check destination file existence and integrity
        if results["destination_exists"]:
            print("\nChecking destination file integrity...")
            dest_checksum = self.calculate_checksum(self.dest_file)
            results["destination_intact"] = (dest_checksum == original_checksum)
            
            if results["destination_intact"]:
                print("✓ Destination file is completely intact!")
            else:
                dest_size = os.path.getsize(self.dest_file)
                source_size = os.path.getsize(self.large_file) if self.large_file.exists() else 0
                print(f"✗ Destination file exists but is incomplete or corrupted!")
                print(f"  Destination size: {dest_size:,} bytes")
                if source_size > 0:
                    print(f"  Source size: {source_size:,} bytes")
                    print(f"  Completion: {100*dest_size/source_size:.1f}%")
        else:
            print("\n✗ Destination file does not exist!")
        
        # Determine journaling status
        journaling_status = self.evaluate_journaling_status(results)
        
        # Display assessment
        print("\n" + "="*60)
        print(f" Journaling Assessment: {journaling_status['status']} ".center(60, "="))
        print("="*60)
        print(f"\n{journaling_status['description']}\n")
        
        # Save results
        self.save_results(results, journaling_status)
        
        return results
    
    def evaluate_journaling_status(self, results):
        """
        Evaluate effectiveness of journaling system based on results.
        
        Args:
            results (dict): Results from verification
            
        Returns:
            dict: Status assessment with description
        """
        if results["source_intact"] and not results["destination_exists"]:
            return {
                "status": "EXCELLENT",
                "description": "Journaling worked perfectly! Operation completely rolled back with source intact."
            }
        elif results["source_exists"] and results["destination_exists"] and results["destination_intact"]:
            return {
                "status": "EXCELLENT",
                "description": "Journaling worked perfectly! Operation completed successfully despite crash."
            }
        elif results["source_intact"] and results["destination_exists"] and not results["destination_intact"]:
            return {
                "status": "GOOD",
                "description": "Journaling worked well! Source preserved, but destination incomplete."
            }
        elif not results["source_exists"] and not results["destination_intact"]:
            return {
                "status": "POOR",
                "description": "Journaling failed! Source lost and destination corrupted."
            }
        elif not results["source_intact"] and not results["destination_intact"]:
            return {
                "status": "POOR",
                "description": "Journaling failed! Both source and destination corrupted."
            }
        else:
            return {
                "status": "UNDEFINED",
                "description": "Unexpected state. Review result details."
            }
    
    def save_results(self, results, journaling_status):
        """
        Save test results to file.
        
        Args:
            results (dict): Test results
            journaling_status (dict): Journaling assessment
            
        Returns:
            Path: Path to the results file
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = self.results_dir / f"{self.fs_type}_real_journaling_{timestamp}.txt"
        
        with open(result_file, 'w') as f:
            f.write(f"Real-world Journaling Test Results\n")
            f.write(f"{'='*60}\n\n")
            f.write(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"OS: {platform.system()} {platform.release()}\n")
            f.write(f"Filesystem: {self.fs_type}\n")
            f.write(f"Test file size: {self.size_gb}GB\n")
            f.write(f"Artificial delay used: {self.use_delay}\n\n")
            
            f.write("Test Results:\n")
            f.write(f"- Source file exists: {results['source_exists']}\n")
            f.write(f"- Source file intact: {results['source_intact']}\n")
            f.write(f"- Destination file exists: {results['destination_exists']}\n")
            f.write(f"- Destination file intact: {results['destination_intact']}\n\n")
            
            f.write(f"Journaling Assessment: {journaling_status['status']}\n")
            f.write(f"{journaling_status['description']}\n\n")
            
            f.write("Summary:\n")
            if journaling_status['status'] in ["EXCELLENT", "GOOD"]:
                f.write(f"{self.fs_type} has effective journaling.\n")
            else:
                f.write(f"{self.fs_type} has limited or ineffective journaling.\n")
        
        print(f"\n✓ Results saved to: {result_file}")
        return result_file


def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(
        description='Real-world Filesystem Journaling Test',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a 2GB test file for NTFS
  python journaling_test.py --type NTFS --size 2 --create
  
  # Run the crash test
  python journaling_test.py --type NTFS --size 2 --test
  
  # Verify results after reboot
  python journaling_test.py --type NTFS --size 2 --verify
  
  # Run test at full speed (harder to time shutdown)
  python journaling_test.py --type NTFS --size 2 --test --no-delay
        """
    )
    
    parser.add_argument('--type', required=True, 
                       help='Filesystem type (e.g., NTFS, ext4, XFS)')
    parser.add_argument('--size', type=int, default=2, 
                       help='File size in GB (default: 2)')
    parser.add_argument('--create', action='store_true', 
                       help='Create large test file')
    parser.add_argument('--test', action='store_true', 
                       help='Start copy test (will prompt for crash)')
    parser.add_argument('--verify', action='store_true', 
                       help='Verify results after crash')
    parser.add_argument('--no-delay', action='store_true', 
                       help='Run copy at normal speed without artificial slowdown')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.size < 1:
        print("Error: File size must be at least 1GB")
        sys.exit(1)
    
    tester = JournalingRealTest(args.type, args.size)
    
    # Set delay option
    if args.no_delay:
        tester.use_delay = False
    
    # Execute requested actions
    if args.create:
        success = tester.create_large_file()
        if not success:
            sys.exit(1)
    
    if args.test:
        success = tester.copy_file_with_progress()
        if not success:
            sys.exit(1)
    
    if args.verify:
        results = tester.verify_after_crash()
        if not results:
            sys.exit(1)
    
    if not (args.create or args.test or args.verify):
        print("Error: Please specify an action: --create, --test, or --verify")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
