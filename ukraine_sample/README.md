---
license: mit
task_categories:
- image-segmentation
- object-detection
tags:
- buildings
- damage-assessment
- satellite-imagery
- ukraine
pretty_name: xBD Ukraine Destruction Analysis
size_categories:
- n<1K
---
Download:
``` python
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id="Rikolrise/xbd-ukraine",
    repo_type="dataset",
    local_dir="./dataset/"
)
```
or using git lfs

```
sudo apt-get install git-lfs
git lfs install
git clone https://huggingface.co/datasets/sda-kr/xbd-ukraine
```