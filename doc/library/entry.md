# Entry

Entries are the units that fill a [library](/doc/library/library.md). Each one corresponds to a file, holding a reference to it along with the metadata associated with it.

### Entry Object Structure

1. `id`:
   - Int, Unique, **Required**
   - The ID for the Entry.
   - Used for internal processing
2. `filename`:
   - String, **Required**
   - The filename with extension of the referenced media file.
3. `path`:
   - String, **Required**, OS Agnostic
   - The folder path in which the media file is located in.
4. [`fields`](/doc/library/field.md):
   - List of dicts, Optional
   - A list of Field ID/Value dicts.

NOTE: _Entries currently have several unused optional fields intended for later features._

## Retrieving Entries based on [Tag](/doc/library/tag.md) Cluster

By default when querying Entries, each Entry's `tags` list (stored in the form of Tag `id`s) is compared against the Tag `id`s in a given Tag cluster (list of Tag `id`s) or appended clusters in the case of multi-term queries. The type of comparison depends on the type of query and whether or not it is an inclusive or exclusive query, or a combination of both. This default searching behavior is done in _O(n)_ time, but can be sped up in the future by building indexes on certain search terms. These indexes can be stored on disk and loaded back into memory in future sessions. These indexes will also need to be updated as new Tags and Entries are added or edited.
