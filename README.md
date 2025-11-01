# Filesystem Journaling Crash Test

A Python-based testing tool designed to evaluate the effectiveness of filesystem journaling by simulating system crashes during file operations. This tool helps assess how well different filesystems (NTFS, ext4, etc.) protect data integrity during unexpected shutdowns.

## Overview

This tool performs real-world crash testing by:
1. Creating a large test file with a known checksum
2. Copying the file to a new location with progress monitoring
3. Prompting the user to forcibly shut down the system at a critical point (40-60% progress)
4. Verifying file integrity after system restart to evaluate journaling effectiveness

## Features

- **Large File Creation**: Generates test files of customizable size (default 2GB)
- **Progress Monitoring**: Real-time progress tracking during file copy operations
- **Checksum Verification**: MD5 checksum validation to ensure data integrity
- **Configurable Speed**: Optional artificial delay for easier manual testing
- **Detailed Reporting**: Generates comprehensive test results with journaling assessment
- **Cross-Platform**: Works on Windows (NTFS) and Linux (ext4, XFS, etc.)

## Requirements

- Python 3.6 or higher
- Sufficient disk space (2x the test file size)
- Administrative/root privileges may be required on some systems

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/filesystem-journaling-crash-test.git
cd filesystem-journaling-crash-test
```

2. No additional dependencies required (uses only Python standard library)

## Usage

### Step 1: Create Test File

Create a large test file (e.g., 2GB):

```bash
python journaling_test.py --type NTFS --size 2 --create
```

Options:
- `--type`: Filesystem type (e.g., NTFS, ext4, XFS)
- `--size`: File size in GB (default: 2)

### Step 2: Run Crash Test

Start the file copy operation:

```bash
python journaling_test.py --type NTFS --size 2 --test
```

The program will:
1. Begin copying the file
2. Display progress in real-time
3. Alert you when progress reaches 40-60%
4. Give you 30 seconds to forcibly shut down your computer

**Important**: You must forcibly shut down (hold power button or disconnect power) - do not use normal shutdown!

Optional: Use `--no-delay` flag for faster copying (harder to time the shutdown):
```bash
python journaling_test.py --type NTFS --size 2 --test --no-delay
```

### Step 3: Verify Results

After rebooting your system, verify the results:

```bash
python journaling_test.py --type NTFS --size 2 --verify
```

The verification will check:
- Source file existence and integrity
- Destination file existence and integrity
- Overall journaling effectiveness

## Journaling Assessment Criteria

The tool evaluates journaling effectiveness with the following ratings:

- **EXCELLENT**: Operation completely rolled back with source intact, OR operation completed successfully
- **GOOD**: Source preserved, destination partially written
- **POOR**: Data loss or corruption in source and/or destination
- **UNDEFINED**: Unexpected state requiring manual review

## Results

Test results are saved in the `fs_test_results` directory with detailed information including:
- Timestamp
- Operating system details
- Filesystem type
- File sizes
- Integrity check results
- Journaling assessment

## Example Output

```
==== VERIFYING FILES AFTER CRASH ====
Source file exists. Checking integrity...
Checksum: a1b2c3d4e5f6...
Source file is completely intact!
Destination file exists. Checking integrity...
Destination file exists but is incomplete or corrupted!

Journaling Assessment: GOOD
Journaling worked well! Source preserved, but destination incomplete.

Results saved to: fs_test_results/NTFS_real_journaling_20250102_143022.txt
```

## Safety Warning

⚠️ **WARNING**: This tool requires forcibly shutting down your computer, which can:
- Cause data loss in other applications
- Potentially corrupt your system if critical OS files are being written
- Damage hardware in rare cases (unlikely but possible)

**Recommendations**:
- Test on a dedicated test system or virtual machine
- Close all other applications before testing
- Backup important data
- Do not test on production systems

## How It Works

### Journaling Basics

Journaling filesystems maintain a log (journal) of changes before committing them to the main filesystem. This helps ensure:
- Consistency after crashes
- Faster recovery times
- Reduced risk of data corruption

### Testing Methodology

1. **Baseline Creation**: A large file is created with a known checksum
2. **Interrupted Operation**: File copy is interrupted mid-operation via forced shutdown
3. **Post-Crash Analysis**: File integrity is verified to assess journaling effectiveness

The test specifically targets the critical 40-60% completion range where partial writes are most likely to expose journaling weaknesses.

## Filesystem Comparison

Expected results for common filesystems:

| Filesystem | Journaling | Expected Result |
|------------|-----------|-----------------|
| NTFS | Yes (metadata) | Good - Source intact, destination may be partial |
| ext4 | Yes (data/metadata) | Excellent - Either rolled back or completed |
| ext3 | Yes (metadata) | Good - Source intact |
| FAT32 | No | Poor - High corruption risk |
| XFS | Yes (metadata) | Good to Excellent |

## Troubleshooting

### "File already exists with correct size"
The test file already exists. You can proceed to `--test` or delete it manually to recreate.

### "Checksum file not found"
Run the `--create` and `--test` steps before running `--verify`.

### Copy completes before shutdown
Use the default speed (without `--no-delay`) or increase file size with `--size` parameter.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is provided as-is for educational and testing purposes. Use at your own risk.

## Disclaimer

This tool is intended for educational purposes and filesystem testing. The authors are not responsible for any data loss, system corruption, or hardware damage resulting from use of this tool. Always test on non-production systems with backed-up data.

## Author

Created for filesystem research and journaling effectiveness testing.
