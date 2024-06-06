# Tag

Tags are user-defined attributes made up of one or more keywords, aliases, and relationships to other tags. A person, place, thing, concept, you name it! Tags allow for a more sophisticated way to organize and search [entries](/doc/library/entry.md) thanks to their aliases, parent tags, and more.
Tags can be as simple or complex as wanted, so that any user can tune TagStudio to fit their needs.

Among the things that make tags so useful, aliases give the ability to contain alternate names and spellings, making searches intuitive and expansive. Furthermore, parent-tags/subtags offer relational organization capabilities for the structuring and connection of the [library's](/doc/library/library.md) contents.

## Tag Object Structure

#### `id`

ID for the tag.

- Int, Unique, Required
- Used for internal processing

#### `name`

The normal name of the tag, with no shortening or specification.

- String, Required
- Doesn't have to be unique
- Used for display, searching, and storing

#### `shorthand`

The shorthand name for the tag. Works like an alias but is used for specific display purposes.

- String, Optional
- Doesn't have to be unique
- Used for display and searching

#### `aliases`

Alternate names for the tag.

- List of Strings, Optional
- Recommended to be unique to this tag
- Used for searching

#### `subtags`

Other Tags that make up properties of this tag. Also called "parent tags".

- List of Strings, Optional
- Used for display (first parent tag only) and searching.

#### `color`

A color name string for customizing the tag's display color

- String, Optional
- Used for display

## Tag Search Examples:

Using for example, a library of files including some tagged with the following tags:

| Tag                 | `name`              | `shorthand` | `aliases`              | `parent tags`                                |
| ------------------- | ------------------- | ----------- | ---------------------- | -------------------------------------------- |
| _League of Legends_ | "League of Legends" | "LoL"       | ["League"]             | ["Game", "Fantasy"]                          |
| _Arcane_            | "Arcane"            | ""          | []                     | ["League of Legends", "Cartoon"]             |
| _Jinx (LoL)_        | "Jinx Piltover"     | "Jinx"      | ["Jinxy", "Jinxy Poo"] | ["League of Legends", "Arcane", "Character"] |
| _Zander (Arcane)_   | "Zander Zanderson"  | "Zander"    | []                     | ["Arcane", "Character"]                      |
| _Mr. Legend (LoL)_  | "Mr. Legend"        | ""          | []                     | ["League of Legends", "Character"]           |

**The query "Arcane" will display results tagged with:**

| Tag             | Cause of Inclusion               | Tag Tree Lineage           |
| --------------- | -------------------------------- | -------------------------- |
| Arcane          | Direct match of tag name         | "Arcane"                   |
| Jinx (LoL)      | Search term is set as parent tag | "Jinx (LoL) > Arcane"      |
| Zander (Arcane) | Search term is set as parent tag | "Zander (Arcane) > Arcane" |

**The query "League of Legends" will display results tagged with:**

| Tag               | Cause of Inclusion                                     | Tag Tree Lineage                               |
| ----------------- | ------------------------------------------------------ | ---------------------------------------------- |
| League of Legends | Direct match of tag name                               | "League of Legends"                            |
| Arcane            | Search term is set as parent tag                       | "Arcane > League of Legends"                   |
| Jinx (LoL)        | Search term is set as parent tag                       | "Jinx (LoL) > League of Legends"               |
| Mr. Legend (LoL)  | Search term is set as parent tag                       | "Mr. Legend (LoL) > League of Legends"         |
| Zander (Arcane)   | Search term is a parent tag of a tag set as parent tag | "Zander (Arcane) > Arcane > League of Legends" |

Note: The query "LoL" will display the same results as the above example since "LoL" is the shorthand for "League of Legends".
