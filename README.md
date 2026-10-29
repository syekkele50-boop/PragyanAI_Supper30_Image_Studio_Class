# Image Applications Studio

Interactive Streamlit app for image cropping, resizing, stacking, blending, watermarks, logos, multiple tags, geometric masks, overlays, frames, collages, and batch operations.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Upload `app.py`, `requirements.txt`, and `README.md` to a GitHub repository.
2. Open https://share.streamlit.io/
3. Create app, select repository and branch, and set the main file path to `app.py`.
4. Deploy.

## Notes
- PNG is recommended for transparency.
- Keep a copy of the original image.
- Watermark only images you own or have permission to edit.
- Publicly deployed apps process uploaded files on the server; avoid confidential images.
