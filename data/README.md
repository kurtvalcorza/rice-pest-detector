# Data in this folder

Labels and split manifests derived from:

> Deleña, R.; Balleras, G.; Dequiña, B. J.; Jumawan, R.; Flores, C. *Annotated light-trap rice pest image dataset with detector-derived region-of-interest crops for species-sex recognition of rice black bug and white stemborer.* Version 1. Zenodo. [doi:10.5281/zenodo.20066074](https://doi.org/10.5281/zenodo.20066074). Licence: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

**No images are included.** The training notebook downloads the archive from Zenodo and checks every image against `split_manifest.json`.

## Changes made to the original

- **New splits.** Images were grouped into families (the original image and its augmented variants), near-duplicate families were merged, and the groups were re-split 70 / 15 / 15 by species composition with a fixed seed. The published train/valid/test split was not kept.
- **One variant per family in validation and test.** Training keeps every variant of its families; validation and test keep one image per family.
- **Polygons to boxes.** 652 label files contained polygon rows; each polygon was converted to its bounding box.
- **Exclusions.** One family (`img_2002`) was excluded because an image had no label file. It is listed, with the reason, in `exclusions.json`.
- **Format.** YOLO labels were converted to COCO JSON (`annotations_{train,val,test}.json`). `split_manifest.json` records each image's family, split, SHA-256, size and source path in the archive.

The rules are in `specs/001-model-training/spec.md` (FR-001 to FR-006) and the checks in `docs/evaluation-record.md`.
