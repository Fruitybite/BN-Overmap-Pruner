# BN-Overmap-Pruner
Overmap Pruner for [Cataclysm: Bright Night](https://github.com/cataclysmbn/Cataclysm-BN), especially for the V2 format save file. Use at own risk.

I made this to use with [Sky Island](https://github.com/graysonchao/CBN-Sky-Island) mod, but might be useful for other purposes.

I made this tool with the help of LLM, so you shouldn't consider this as a reliable reference.

If you have any ideas for improving this, feel free to submit a pull request and ping me at the BN discord.

README Korean Version : https://github.com/Fruitybite/BN-Overmap-Pruner/blob/main/README_KO.md

## Usage
0. BACKUP YOUR SAVE FILE BEFORE USE
   - I tested this before uploading, but this may cause critical errors and/or even save file corruption.
 1. Download the file and put into your save directory
 2. Install python from https://www.python.org/
    - I'm currently using python 3.10.8, but any latest version should work well.
 3. Set your in-game overmap coordinates format option as "Absolute"
 4. Write down the submap's coordinates which you want to preserve
 5. Open command prompt or Windows terminal at your save directory
 6. Input the proper command with the coords
    - IMPORTANT : This tool deletes ALL overmaps and submaps except for those you specify.
    - Automatic backup : This tool will create auto-save file as `map.sqlite3.bak` (or similiar extensions) in the same directory. If something goes wrong, find and rename it. But please do not rely solely on this feature. I strongly recommend making a separate backup manually as well.

## Commands

`overmap_pruner.py [-h] (--keep KEEP | --keep-file KEEP_FILE | --interactive) [--span SPAN] [--no-vacuum] [--dry-run] [--force] [--remove-grids] [--verify-against VERIFY_AGAINST] [--verify-only] [db]`

  **--keep KEEP** : Enter the desired coordinates manually.
  
  Enclose the entire set of coordinates in quotation marks (""). A period (.) is used to separate X, Y, and Z within a single coordinate, and a comma (,) is used to separate different coordinates.
  
  For example, `"119.183.9, 119.183.10"` specifies the two submaps `119,183,9` and `119,183,10` based on the in-game overmap coordinates format with the "Absolute" option selected.
  
  e.g.) `python overmap_pruner.py --keep "119.183.9"`
  
  **--keep-file KEEP_FILE** : Write the desired coordinates in seperate file and put it together with pruner.
  
  Put one coordinate per line. Same as using the `--keep` option, but I recommend this method since this would cause lesser typing errors.

  e.g.) `python overmap_pruner.py --keep-file keep.txt`
  
  **--interactive** : Enter the desired coordinates manually.

  Similar to `--keep` option, but this option requires you to enter the coordinates separately.

  e.g.) `python overmap_pruner.py --interactive`

  **--span SPAN** : Enter the desired coordinate span.

  e.g.) `python overmap_pruner.py --span 180`
  
  BN's overmap coordinate span is 180 - so this option's default is also 180. DO NOT CHANGE THIS unless you know what you are doing.

  **--no-vacuum** : Skip `VACUUM` at end.

  This will skip the `VACUUM`, the optimization sequence. This will make operation faster, but the save file size might be larger compared to when this option isn't used.

  e.g.) `python overmap_pruner.py (--keep KEEP | --keep-file KEEP_FILE | --interactive) --no-vacuum`

  **--dry-run** : Show the pruning plan, but do not change actual file.

  This will show the preserved submap coordinates and overmaps, but does not actually modify the file. Suitable for testing purposes.

  e.g.) `python overmap_pruner.py (--keep KEEP | --keep-file KEEP_FILE | --interactive) --dry-run`

  **--force** : Skip the confirmation.

  Do not use this unless you made a backup.

  e.g.) `python overmap_pruner.py (--keep KEEP | --keep-file KEEP_FILE | --interactive) --force`

  **--remove-grid** : Remove ALL electric/fluid grid data in kept overmaps.

  Default option is preserving and restoring grid data. May cause error and even may not work as intended.
  
  Use only when you really need this.

  e.g.) `python overmap_pruner.py (--keep KEEP | --keep-file KEEP_FILE | --interactive) --remove-grid`

  **--verify-against VERIFY_AGAINST** : Compare map.sqlite3 and other seperate `map.sqlite3` file.

  e.g.) `python overmap_pruner.py (--keep KEEP | --keep-file KEEP_FILE | --interactive) --verify-against map_old.sqlite3`

  **--verify-only** : Use with `--verify-against` option to run verification and do not prune.

  e.g.) `python overmap_pruner.py (--keep KEEP | --keep-file KEEP_FILE | --interactive) --verify-against map_old.sqlite3 --verify-only`

  **db** : Path to `map.sqlite3`.

  If omitted, will try `./map.sqlite3` in the script folder.
