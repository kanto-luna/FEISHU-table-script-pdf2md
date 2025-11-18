# Something Before Work

In this document i will tell you WHAT i want to do and HOW do i do as simple as i can.


## Why is the project there ?

There are so many PRs in the table, they are all unreadable in the columns directly cause they're all PDF. HRs want to read it as common text field.


## What does the project do ?

There are following three main steps through full process.

1. Downloads PDF in all records and translates them into MD.
2. Reads all MD and records their context.
3. Uploads above context as text and uploads MD/ZIP as file.


## How does the project works ? 

Script will scan all records in the origin table and find out lines where the **target columns** is empty and the **origin columns** is no empty.

Then the script will download all of above records as `*.pdf`.

When downloading is done, the script will translate all PDF into ZIP includes MD and extra files like IMG.

Script will unzip all of ZIP and save target in a prepared folder after that. by the way, script will also read context in each `*.md`.

In the end script will upload all of ZIP and context to target FEISHU table.
