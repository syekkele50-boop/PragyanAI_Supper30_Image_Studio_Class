import io
import zipfile
from pathlib import Path

import numpy as np
import streamlit as st
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageEnhance, ImageFilter

st.set_page_config(page_title="PragyanAI- Image Applications Studio", page_icon="🧩", layout="wide")

st.title("PragyanAI - Image Applications Studio")
st.image("PragyanAI_Transperent.png")
st.caption("Crop • Stack • Merge • Watermark • Mask • Overlay • Logo • Tags • Export")

st.markdown("""
An interactive image utility workbench for common image editing and compositing tasks.
Upload images, choose a tool, adjust settings, preview the result, and download your output.
""")

TOOLS = [
    "Crop Image", "Resize Image", "Stack Images", "Merge / Blend Two Images",
    "Add Text Watermark", "Add Logo / Image Watermark", "Add Multiple Tags",
    "Mask a Specific Region", "Overlay / Embed an Image", "Add Border / Frame",
    "Collage / Contact Sheet", "Remove Background (manual mask)", "Image Composition",
    "Batch Process Images"
]
tool = st.sidebar.selectbox("Choose an application", TOOLS)
st.sidebar.markdown("---")
st.sidebar.markdown("**Tips**\n- Use PNG for transparency.\n- Keep an untouched original copy.\n- Respect image ownership and watermark permissions.")

def load_rgb(file):
    return ImageOps.exif_transpose(Image.open(file)).convert("RGBA")

def pil_bytes(img, fmt="PNG"):
    buf = io.BytesIO()
    if fmt.upper() == "JPEG":
        img = img.convert("RGB")
    img.save(buf, format=fmt)
    return buf.getvalue()

def get_font(size):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        "/Library/Fonts/Arial.ttf"
    ]
    for p in candidates:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size=size)
            except Exception:
                pass
    return ImageFont.load_default()

def contain(img, size, bg=(245,245,245,255)):
    canvas = Image.new("RGBA", size, bg)
    copy = img.copy()
    copy.thumbnail(size, Image.Resampling.LANCZOS)
    x = (size[0]-copy.width)//2
    y = (size[1]-copy.height)//2
    canvas.alpha_composite(copy, (x,y))
    return canvas

def apply_round_tag(base, text, x, y, font_size, fill, text_color, padding=12):
    draw = ImageDraw.Draw(base, "RGBA")
    font = get_font(font_size)
    bbox = draw.textbbox((0,0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    draw.rounded_rectangle((x, y, x+tw+padding*2, y+th+padding*2), radius=12, fill=fill)
    draw.text((x+padding, y+padding-bbox[1]), text, font=font, fill=text_color)
    return base

def crop_tool(img):
    st.subheader("Crop Image")
    w, h = img.size
    c1,c2,c3,c4 = st.columns(4)
    with c1: left = st.slider("Left (%)", 0, 90, 5)
    with c2: top = st.slider("Top (%)", 0, 90, 5)
    with c3: right = st.slider("Right (%)", 10, 100, 95)
    with c4: bottom = st.slider("Bottom (%)", 10, 100, 95)
    x1, y1 = int(w*left/100), int(h*top/100)
    x2, y2 = int(w*right/100), int(h*bottom/100)
    if x2 <= x1 or y2 <= y1:
        st.error("Right and bottom boundaries must be greater than left and top.")
        return img
    st.caption(f"Crop rectangle: ({x1}, {y1}) to ({x2}, {y2})")
    return img.crop((x1,y1,x2,y2))

def resize_tool(img):
    st.subheader("Resize Image")
    c1,c2,c3 = st.columns(3)
    with c1: width = st.number_input("Width", min_value=1, max_value=12000, value=img.width)
    with c2: keep = st.checkbox("Keep aspect ratio", value=True)
    with c3: scale_method = st.selectbox("Resampling", ["High quality (Lanczos)", "Bicubic", "Bilinear", "Nearest"])
    if keep:
        height = max(1, int(width * img.height / img.width))
        st.write(f"Calculated height: **{height}px**")
    else:
        height = st.number_input("Height", min_value=1, max_value=12000, value=img.height)
    method = {"High quality (Lanczos)":Image.Resampling.LANCZOS, "Bicubic":Image.Resampling.BICUBIC, "Bilinear":Image.Resampling.BILINEAR, "Nearest":Image.Resampling.NEAREST}[scale_method]
    return img.resize((int(width),int(height)), method)

def stack_tool(files, mode):
    imgs = [load_rgb(f) for f in files]
    if len(imgs) < 2:
        st.warning("Upload at least two images in the multi-image uploader.")
        return None
    gap = st.slider("Gap between images (px)", 0, 100, 12)
    bg_color = st.color_picker("Background color", "#F2F2F2")
    bg = tuple(bytes.fromhex(bg_color.lstrip("#"))) + (255,)
    if mode == "Horizontal":
        target_h = max(i.height for i in imgs)
        resized = [i.resize((max(1,round(i.width*target_h/i.height)),target_h),Image.Resampling.LANCZOS) for i in imgs]
        canvas = Image.new("RGBA",(sum(i.width for i in resized)+gap*(len(resized)-1),target_h),bg)
        x=0
        for im in resized:
            canvas.alpha_composite(im,(x,0)); x += im.width+gap
    else:
        target_w = max(i.width for i in imgs)
        resized = [i.resize((target_w,max(1,round(i.height*target_w/i.width))),Image.Resampling.LANCZOS) for i in imgs]
        canvas = Image.new("RGBA",(target_w,sum(i.height for i in resized)+gap*(len(resized)-1)),bg)
        y=0
        for im in resized:
            canvas.alpha_composite(im,(0,y)); y += im.height+gap
    return canvas

def blend_tool(img, second):
    st.subheader("Merge / Blend Two Images")
    c1,c2,c3 = st.columns(3)
    with c1: mode = st.selectbox("Fit second image", ["Cover first image", "Contain on canvas", "Stretch to exact size"])
    with c2: alpha = st.slider("Second image opacity", 0.0, 1.0, 0.5, 0.05)
    with c3: blend = st.selectbox("Blend mode", ["Alpha blend", "Screen", "Multiply", "Difference"])
    base = img.copy()
    if mode == "Cover first image":
        sec = ImageOps.fit(second, base.size, method=Image.Resampling.LANCZOS)
    elif mode == "Contain on canvas":
        sec = contain(second, base.size, (0,0,0,0))
    else:
        sec = second.resize(base.size, Image.Resampling.LANCZOS)
    a = np.asarray(base.convert("RGB")).astype(np.float32)
    b = np.asarray(sec.convert("RGB")).astype(np.float32)
    if blend == "Alpha blend":
        out = a*(1-alpha)+b*alpha
    elif blend == "Screen":
        out = 255-(255-a)*(255-b)/255
        out = a*(1-alpha)+out*alpha
    elif blend == "Multiply":
        out = a*b/255
        out = a*(1-alpha)+out*alpha
    else:
        out = np.abs(a-b)
        out = a*(1-alpha)+out*alpha
    return Image.fromarray(np.uint8(np.clip(out,0,255))).convert("RGBA")

def text_watermark(img):
    st.subheader("Text Watermark")
    text = st.text_input("Watermark text", "© PragyanAI")
    c1,c2,c3,c4 = st.columns(4)
    with c1: pos = st.selectbox("Position", ["Bottom right","Bottom left","Top right","Top left","Center"])
    with c2: size = st.slider("Font size", 10, 120, max(20,min(42,img.width//18)))
    with c3: opacity = st.slider("Opacity", 10, 100, 65)
    with c4: margin = st.slider("Margin (px)", 0, 100, 20)
    color = st.color_picker("Text color", "#FFFFFF")
    stroke = st.checkbox("Add dark outline", True)
    out = img.copy()
    draw = ImageDraw.Draw(out, "RGBA")
    font = get_font(size)
    bbox = draw.textbbox((0,0), text, font=font, stroke_width=2 if stroke else 0)
    tw,th = bbox[2]-bbox[0],bbox[3]-bbox[1]
    xy = {
        "Bottom right":(img.width-tw-margin,img.height-th-margin),
        "Bottom left":(margin,img.height-th-margin),
        "Top right":(img.width-tw-margin,margin),
        "Top left":(margin,margin),
        "Center":((img.width-tw)//2,(img.height-th)//2)
    }[pos]
    rgba = tuple(bytes.fromhex(color.lstrip("#"))) + (int(255*opacity/100),)
    draw.text(xy, text, font=font, fill=rgba, stroke_width=2 if stroke else 0, stroke_fill=(0,0,0,int(220*opacity/100)) if stroke else None)
    return out

def logo_watermark(img, logo_file):
    logo = load_rgb(logo_file)
    st.subheader("Logo / Image Watermark")
    c1,c2,c3 = st.columns(3)
    with c1: scale = st.slider("Logo width (% of base)", 5, 60, 20)
    with c2: opacity = st.slider("Logo opacity (%)", 5, 100, 75)
    with c3: pos = st.selectbox("Logo position", ["Bottom right","Bottom left","Top right","Top left","Center"])
    margin = st.slider("Logo margin", 0, 100, 20)
    new_w = max(1,int(img.width*scale/100))
    new_h = max(1,int(logo.height*new_w/logo.width))
    logo = logo.resize((new_w,new_h),Image.Resampling.LANCZOS)
    alpha = logo.getchannel("A").point(lambda v:int(v*opacity/100))
    logo.putalpha(alpha)
    coords = {
        "Bottom right":(img.width-logo.width-margin,img.height-logo.height-margin),
        "Bottom left":(margin,img.height-logo.height-margin),
        "Top right":(img.width-logo.width-margin,margin),
        "Top left":(margin,margin),
        "Center":((img.width-logo.width)//2,(img.height-logo.height)//2)
    }[pos]
    out=img.copy()
    out.alpha_composite(logo,coords)
    return out

def multiple_tags(img):
    st.subheader("Multiple Tags / Labels")
    raw = st.text_area("Enter one tag per line", "PragyanAI\nComputer Vision\nAI Education")
    tags = [x.strip() for x in raw.splitlines() if x.strip()]
    c1,c2,c3 = st.columns(3)
    with c1: size = st.slider("Tag font size", 10, 64, 24)
    with c2: placement = st.selectbox("Layout", ["Top left", "Top right", "Bottom left", "Bottom right", "Top row", "Bottom row"])
    with c3: gap = st.slider("Tag gap", 0, 40, 10)
    bg_hex = st.color_picker("Tag background", "#132A4A")
    fg_hex = st.color_picker("Tag text", "#FFFFFF")
    opacity = st.slider("Tag background opacity (%)", 10, 100, 85)
    out=img.copy()
    fill=tuple(bytes.fromhex(bg_hex.lstrip("#")))+(int(255*opacity/100),)
    text_color=tuple(bytes.fromhex(fg_hex.lstrip("#")))+(255,)
    font=get_font(size)
    pad=10
    draw=ImageDraw.Draw(out,"RGBA")
    x,y=20,20
    for tag in tags:
        bb=draw.textbbox((0,0),tag,font=font)
        tw,th=bb[2]-bb[0],bb[3]-bb[1]
        twp,thp=tw+pad*2,th+pad*2
        if placement in ("Top right","Bottom right"):
            xx=img.width-twp-20
        elif placement in ("Top left","Bottom left"):
            xx=20
        else:
            xx=x
        if placement in ("Bottom left","Bottom right","Bottom row"):
            yy=img.height-thp-20
        else:
            yy=20
        draw.rounded_rectangle((xx,yy,xx+twp,yy+thp),radius=10,fill=fill)
        draw.text((xx+pad,yy+pad-bb[1]),tag,font=font,fill=text_color)
        if placement in ("Top row","Bottom row"):
            x += twp+gap
            if x+twp > img.width-20:
                x=20
                y += thp+gap
        elif placement in ("Top left","Bottom left"):
            y += thp+gap
        elif placement in ("Top right","Bottom right"):
            y += thp+gap
    return out

def mask_tool(img):
    st.subheader("Mask a Specific Region")
    st.info("This tool creates geometric masks. For hand-drawn masks, use an image editor or add a dedicated drawing-canvas component.")
    shape = st.selectbox("Mask shape", ["Rectangle","Ellipse","Polygon (4-point demo)"])
    c1,c2,c3,c4 = st.columns(4)
    with c1: x = st.slider("X (%)",0,95,25)
    with c2: y = st.slider("Y (%)",0,95,25)
    with c3: ww = st.slider("Width (%)",5,100,40)
    with c4: hh = st.slider("Height (%)",5,100,40)
    mode=st.selectbox("Outside region", ["Make outside transparent","Blur outside","Grayscale outside","Keep only masked region"])
    x1,y1=int(img.width*x/100),int(img.height*y/100)
    x2,y2=min(img.width,x1+int(img.width*ww/100)),min(img.height,y1+int(img.height*hh/100))
    mask=Image.new("L",img.size,0)
    d=ImageDraw.Draw(mask)
    if shape=="Rectangle": d.rectangle((x1,y1,x2,y2),fill=255)
    elif shape=="Ellipse": d.ellipse((x1,y1,x2,y2),fill=255)
    else: d.polygon([(x1,y1),(x2,y1),(x2,y2),(x1,y2)],fill=255)
    if mode in ("Make outside transparent","Keep only masked region"):
        out=img.copy()
        if mode=="Make outside transparent":
            out.putalpha(mask)
        else:
            out.putalpha(mask)
        return out
    if mode=="Blur outside":
        changed=img.filter(ImageFilter.GaussianBlur(radius=12))
    else:
        changed=ImageOps.grayscale(img).convert("RGBA")
    return Image.composite(img,changed,mask)

def overlay_tool(img, second):
    st.subheader("Overlay / Embed an Image")
    c1,c2,c3 = st.columns(3)
    with c1: scale=st.slider("Overlay width (%)",5,100,25)
    with c2: opacity=st.slider("Overlay opacity (%)",0,100,80)
    with c3: pos=st.selectbox("Overlay position",["Bottom right","Bottom left","Top right","Top left","Center"])
    xoff=st.slider("Extra horizontal offset (px)",-500,500,0,5)
    yoff=st.slider("Extra vertical offset (px)",-500,500,0,5)
    nw=max(1,int(img.width*scale/100))
    nh=max(1,int(second.height*nw/second.width))
    overlay=second.resize((nw,nh),Image.Resampling.LANCZOS)
    overlay.putalpha(overlay.getchannel("A").point(lambda v:int(v*opacity/100)))
    pos0={
        "Bottom right":(img.width-nw-20,img.height-nh-20),
        "Bottom left":(20,img.height-nh-20),
        "Top right":(img.width-nw-20,20),
        "Top left":(20,20),
        "Center":((img.width-nw)//2,(img.height-nh)//2)
    }[pos]
    out=img.copy()
    out.alpha_composite(overlay,(pos0[0]+xoff,pos0[1]+yoff))
    return out

def border_tool(img):
    st.subheader("Border / Frame")
    c1,c2=st.columns(2)
    with c1: width=st.slider("Border width",1,200,20)
    with c2: color=st.color_picker("Border color","#FFFFFF")
    rgba=tuple(bytes.fromhex(color.lstrip("#")))+(255,)
    return ImageOps.expand(img,border=width,fill=rgba)

def collage_tool(files):
    imgs=[load_rgb(f) for f in files]
    if not imgs:
        return None
    cols=st.slider("Number of columns",1,5,min(3,len(imgs)))
    thumb_w=st.slider("Thumbnail width",100,600,240,20)
    thumb_h=st.slider("Thumbnail height",80,500,180,20)
    label=st.checkbox("Add filenames under images",True)
    gap=16
    rows=(len(imgs)+cols-1)//cols
    cell_h=thumb_h+(36 if label else 0)
    canvas=Image.new("RGBA",(cols*thumb_w+(cols+1)*gap,rows*cell_h+(rows+1)*gap),(245,245,245,255))
    d=ImageDraw.Draw(canvas)
    font=get_font(14)
    for i,(im,f) in enumerate(zip(imgs,files)):
        x=gap+(i%cols)*(thumb_w+gap); y=gap+(i//cols)*(cell_h+gap)
        thumb=contain(im,(thumb_w,thumb_h))
        canvas.alpha_composite(thumb,(x,y))
        if label:
            d.text((x,y+thumb_h+6),f.name[:32],font=font,fill=(25,25,25,255))
    return canvas

def batch_tool(files):
    if not files:
        st.warning("Upload multiple images using the multi-image uploader below.")
        return
    operation=st.selectbox("Batch operation",["Resize to width","Convert to grayscale","Add text watermark","Add border"])
    width=st.number_input("Target width",min_value=64,max_value=6000,value=800)
    watermark=st.text_input("Batch watermark text","© PragyanAI")
    result={}
    for f in files:
        im=load_rgb(f)
        if operation=="Resize to width":
            im=im.resize((int(width),max(1,int(im.height*width/im.width))),Image.Resampling.LANCZOS)
        elif operation=="Convert to grayscale":
            im=ImageOps.grayscale(im).convert("RGBA")
        elif operation=="Add text watermark":
            d=ImageDraw.Draw(im,"RGBA"); font=get_font(max(14,im.width//35))
            d.text((12,im.height-40),watermark,font=font,fill=(255,255,255,190),stroke_width=2,stroke_fill=(0,0,0,180))
        else:
            im=ImageOps.expand(im,border=12,fill=(255,255,255,255))
        result[f.name.rsplit(".",1)[0]+".png"]=im
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,"w",zipfile.ZIP_DEFLATED) as z:
        for name,im in result.items():
            z.writestr(name,pil_bytes(im))
    st.download_button("Download all processed images (ZIP)",buf.getvalue(),"processed_images.zip","application/zip")
    st.success(f"Prepared {len(result)} images.")

main_upload=st.file_uploader("Upload base image",type=["png","jpg","jpeg","webp","bmp","tif","tiff"],key="base")
multi_files=st.file_uploader("Upload multiple images (for stacking, collage, batch)",type=["png","jpg","jpeg","webp","bmp","tif","tiff"],accept_multiple_files=True,key="multi")
if tool in ("Stack Images","Collage / Contact Sheet","Batch Process Images"):
    if tool=="Stack Images":
        if multi_files:
            direction=st.radio("Stack direction",["Horizontal","Vertical"],horizontal=True)
            result=stack_tool(multi_files,direction)
            if result:
                st.image(result,caption="Stacked output",use_container_width=True)
                st.download_button("Download stacked image",pil_bytes(result),"stacked.png","image/png")
        else:
            st.info("Upload at least two images using the multi-image uploader.")
    elif tool=="Collage / Contact Sheet":
        if multi_files:
            result=collage_tool(multi_files)
            if result:
                st.image(result,caption="Contact sheet",use_container_width=True)
                st.download_button("Download contact sheet",pil_bytes(result),"contact_sheet.png","image/png")
        else:
            st.info("Upload multiple images to create a contact sheet.")
    else:
        batch_tool(multi_files)
    st.stop()

if not main_upload:
    st.info("Upload a base image to start. For merge, overlay, or logo watermark tools, upload a second image when prompted.")
    st.stop()

try:
    original=load_rgb(main_upload)
except Exception as e:
    st.error(f"Could not open image: {e}")
    st.stop()

second=None
if tool in ("Merge / Blend Two Images","Add Logo / Image Watermark","Overlay / Embed an Image"):
    second_file=st.file_uploader("Upload second image / logo / overlay",type=["png","jpg","jpeg","webp","bmp","tif","tiff"],key="second")
    if second_file:
        second=load_rgb(second_file)

if tool=="Crop Image":
    result=crop_tool(original)
elif tool=="Resize Image":
    result=resize_tool(original)
elif tool=="Merge / Blend Two Images":
    result=blend_tool(original,second) if second else None
elif tool=="Add Text Watermark":
    result=text_watermark(original)
elif tool=="Add Logo / Image Watermark":
    result=logo_watermark(original,second_file) if second else None
elif tool=="Add Multiple Tags":
    result=multiple_tags(original)
elif tool=="Mask a Specific Region":
    result=mask_tool(original)
elif tool=="Overlay / Embed an Image":
    result=overlay_tool(original,second) if second else None
elif tool=="Add Border / Frame":
    result=border_tool(original)
elif tool=="Image Composition":
    st.subheader("Image Composition")
    st.write("Use the merge, overlay, and tag tools to create a composition. This starter module previews the uploaded image.")
    result=original
else:
    result=original

if result is None:
    st.info("Upload the required second image to continue.")
    st.stop()

st.markdown("---")
st.subheader("Preview and Export")
c1,c2=st.columns(2)
with c1:
    st.markdown("**Original**")
    st.image(original, use_container_width=True)
with c2:
    st.markdown("**Output**")
    st.image(result, use_container_width=True)
fmt=st.selectbox("Download format",["PNG","JPEG","WEBP"])
name=st.text_input("Output filename","image_output")
ext=fmt.lower()
st.download_button(f"Download output ({fmt})",pil_bytes(result,fmt),f"{name}.{ext}",f"image/{ext}")
st.caption("Privacy note: uploaded images are processed by this app's running server. Do not upload confidential or personally identifiable images to a public deployment.")
