# Model cards: rice-pest detector

> **⚠️ Notice.** For research, training and evaluation only. Not validated for production, clinical, diagnostic or safety-critical use, and not a field pest-surveillance or pest-alert system. The models' counts are experimental estimates: they are not agronomic advice, must not be the basis for any pest-management or spraying decision, and should be reviewed by a qualified person. Results are tutorial evidence, not benchmarks. Everything is provided "as is", without warranty of any kind. To the maximum extent permitted by law, the maintainers accept no liability for its use.
>
> This is a teaching and demonstration project, made for the *Coding with AI Agents* workshop. It is not an official tool, product or service of any organisation or government agency, and no organisation endorses it. The models are **not made for farmers** and have not been validated in the field.

Each fine-tuned model has its own card:

- [r50-v5: RT-DETR with a ResNet-50-vd backbone](model-cards/r50-v5.md), fine-tuned from `PekingU/rtdetr_r50vd`, 640×640.
- [RF-DETR-M: RF-DETR, medium](model-cards/rf-detr-m.md), fine-tuned from `Roboflow/rf-detr-medium`, 576×576.
- [D-FINE-L: D-FINE, large](model-cards/d-fine-l.md), fine-tuned from `ustc-community/dfine-large-coco`, 640×640.

**The demo app uses r50-v5 by default**, at counting threshold 0.48. It was chosen on validation under rules fixed before any result, and it is the only model whose test result was a pre-registered evaluation. RF-DETR-M and D-FINE-L are comparison models: the app can download or import them, and it shows a "not validated" banner on their counts. Every model, the default included, carries a "Not validated" tag in the app's model list: none has been validated in the field or by experts, and the release gates (field validation, wording review, data protection, phone latency) are still open.

Every figure in the cards, with its provenance, is in [`evaluation-record.md`](evaluation-record.md).

**Licences.** The base models are Apache-2.0. The training data is CC BY 4.0 with attribution (see `NOTICE` and [`data/README.md`](../data/README.md)). The repository code is Apache-2.0. The trained weights are not in this repository: the ONNX files are published on [Kaggle](https://www.kaggle.com/models/kurtvalcorza/rice-pest-detector) under Apache-2.0, one variation per model ([r50-v5](https://www.kaggle.com/models/kurtvalcorza/rice-pest-detector/Onnx/r50-v5), [rf-detr-m](https://www.kaggle.com/models/kurtvalcorza/rice-pest-detector/Onnx/rf-detr-m), [d-fine-l](https://www.kaggle.com/models/kurtvalcorza/rice-pest-detector/Onnx/d-fine-l)), each with a copy of its card. They are a teaching demo, not validated in the field and not for farmers.
