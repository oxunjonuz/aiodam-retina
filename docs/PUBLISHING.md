# Publishing to GitHub

English is the primary language: `README.md` and `docs/REPORT_EN.md`.
`README_RU.md` and `docs/REPORT_RU.md` are optional Russian translations.

## Suggested repository details

- Name: `aiodam-retina`
- Description: `Spatial and temporal perception for LLM agents on discrete grids: explicit XY coordinates, change events, and action-observation history.`
- Suggested topics: `llm`, `perception`, `grid-world`, `spatial-reasoning`, `python`.

## Browser upload

1. Sign in to GitHub and open [Create a new repository](https://github.com/new).
2. Enter the name and description. A private staging repository is an option
   while you review the license and fixture permissions; choose visibility
   deliberately because a public repository exposes its uploaded contents.
3. Leave automatic README, license and gitignore generation off: this folder
   already contains its README, gitignore and selected `LICENSE`.
4. Create the repository. Select **uploading an existing file** on its empty
   page, or **Add file > Upload files** if it already contains files.
5. Unzip `retina-public-candidate-20260911.zip` locally. Upload the CONTENTS of
   the extracted directory, preserving its subdirectories. `README.md`,
   `pyproject.toml`, `retina/`, `tests/`, `docs/` and `evidence/` must be at the
   repository root. Do not upload only the ZIP as the repository source.
6. Include `.gitignore` as well; your file browser may hide dotfiles.
7. Review the upload list. Do not include the owner's private review archive,
   local source map, credentials, caches, build output or game-session files.
8. Commit with a message such as `Initial Retina release candidate`.
9. Check that the English README renders and its relative links open. Review
   `NOTICE.md` and `docs/RELEASE_CHECKLIST.md` before a public release.

GitHub's browser upload supports up to 100 files at once and up to 25 MiB per
file. This candidate fits within those limits. See the official
[file upload documentation](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository).

## Before making it public

The owner selected PolyForm Noncommercial 1.0.0 and a separate paid commercial
licensing route. Preserve `LICENSE`, `NOTICE.md` and `COMMERCIAL_LICENSE.md`.
Confirm the applicable rights and contributor obligations before publication.
Verify redistribution permission for the included ARC game frames separately.
No GitHub account token belongs in the code or documentation.

Publishing this candidate does not establish a VLM benchmark win or an official
ARC score. Keep the measured context reduction, sensor runtime and historical
gameplay applications as separate claims.
