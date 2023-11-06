"""
Python script to remove data folders (a.k.a. Larian's data) from git tracking but retain folder names
"""

import glob
for folder in glob.glob("data/*"):
    with open(f"{folder}/.gitignore", "w") as file:
        file.write("""
*
!.gitignore
        """)
        file.close()