# Tools & Macros

Tools and macros are features that serve to create a more fluid [library](/doc/library/library.md)-managing process, or provide some extra functionality. Please note that some are still in active development and will be fleshed out in future updates.

## Tools

### Fix Unlinked Entries

This tool displays the number of unlinked [entries](/doc/library/entry.md), and some options for their resolution.

1. Refresh
   - Scans through the library and updates the unlinked entry count.
2. Search & Relink
   - Attempts to automatically find and reassign missing files.
3. Delete Unlinked Entries
   - Displays a confirmation prompt containing the list of all missing files to be deleted before committing to or cancelling the operation.

### Fix Duplicate Files

This tool allows for management of duplicate files in the library using a [DupeGuru](https://dupeguru.voltaicideas.net/) file.

1. Load DupeGuru File
   - load the "results" file created from a DupeGuru scan
2. Mirror Entries
   - Duplicate entries will have their contents mirrored across all instances. This allows for duplicate files to then be deleted with DupeGuru as desired, without losing the [field](/doc/library/field.md) data that has been assigned to either. (Once deleted, the "Fix Unlinked Entries" tool can be used to clean up the duplicates)

### Create Collage

This tool is a preview of an upcoming feature. When selected, TagStudio will generate a collage of all the contents in a Library, which can be found in the Library folder ("/your-folder/.TagStudio/collages/"). Note that this feature is still in early development, and doesn't yet offer any customization options.

## Macros

### Auto-fill [WIP]

Tool is in development and will be documented in future update.

### Sort fields

Tool is in development, will allow for user-defined sorting of [fields](/doc/library/field.md).

### Folders to Tags

Creates tags from the existing folder structure in the library, which are previewed in a hierarchy view for the user to confirm. A tag will be created for each folder and applied to all entries, with each subfolder being linked to the parent folder as a [parent tag](/doc/library/tag.md#subtags). Tags will initially be named after the folders, but can be fully edited and customized afterwards.
