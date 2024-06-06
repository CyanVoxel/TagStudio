# Field

Fields are the building blocks of metadata stored in [entries](/doc/library/entry.md). Fields have several base types for representing different kinds of information, including:

#### `text_line`

- A string of text, displayed as a single line.
  - e.g: Title, Author, Artist, URL, etc.

#### `text_box`

- A long string of text displayed as a box of text.
  - e.g: Description, Notes, etc.

#### `tag_box`

- A box of [tags](/doc/library/tag.md) defined and added by the user.
- Multiple tag boxes can be used to separate classifications of tags.
  - e.g: Content Tags, Meta Tags, etc.

#### `datetime` [WIP]

- A date and time value.
  - e.g: Date Created, Date Modified, Date Taken, etc.

#### `checkbox` [WIP]

- A simple two-state checkbox.
- Can be associated with a tag for quick organization.
  - e.g: Archive, Favorite, etc.

#### `collation` [obsolete]

- Previously used for associating files to be used in a [collation](/doc/utilities/macro.md#create-collage), will be removed in favor of a more flexible feature in future updates.
