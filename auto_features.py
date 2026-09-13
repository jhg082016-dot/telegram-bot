import re
import os

SEARCH_TRIGGERS = [
    "найди в интернете", "поищи в интернете", "загугли", "что нового",
    "новости про", "последние новости", "погода в", "погода на",
    "курс доллара", "курс евро", "курс биткоина", "актуально про",
    "дай ссылку на", "поиск в интернете", "сколько стоит",
    "как сейчас", "что сейчас", "найди информацию"
]

def needs_search(text):
    if not text: return False
    low = text.lower()
    if any(t in low for t in SEARCH_TRIGGERS):
        return True
    if re.search(r'https?://\S+', text):
        return True
    return False

def extract_query(text):
    for t in SEARCH_TRIGGERS:
        text = re.sub(re.escape(t), "", text, flags=re.IGNORECASE)
    text = re.sub(r'https?://\S+', "", text)
    return text.strip() or "актуальные новости"

def needs_plot(text):
    if not text: return False
    low = text.lower()
    return ("график" in low or "построй" in low) and bool(re.search(r'\d', low))

def extract_numbers(text):
    nums = re.findall(r'-?\d+\.?\d*', text)
    return [float(n) if '.' in n else int(n) for n in nums]

def make_plot(numbers, title="График"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(numbers, marker='o', linewidth=2, color='#4a90d9')
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    path = "/app/tmp_files/plot.png"
    os.makedirs("/app/tmp_files", exist_ok=True)
    fig.savefig(path, dpi=100, bbox_inches='tight')
    plt.close(fig)
    return path

def file_action_from_ext(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        return "pdf_menu"
    if ext in (".docx", ".doc"):
        return "docx_menu"
    if ext in (".py", ".js", ".sh", ".php"):
        return "code_menu"
    if ext in (".jpg", ".jpeg", ".png", ".webp"):
        return "img_menu"
    return None

def convert_pdf_to_txt(src, dst):
    from pypdf import PdfReader
    reader = PdfReader(src)
    with open(dst, "w", encoding="utf-8") as f:
        for page in reader.pages:
            f.write((page.extract_text() or "") + "\n")
    return dst

def convert_docx_to_txt(src, dst):
    import docx
    d = docx.Document(src)
    with open(dst, "w", encoding="utf-8") as f:
        for p in d.paragraphs:
            f.write(p.text + "\n")
    return dst

def convert_docx_to_pdf(src, dst):
    import subprocess
    out_dir = os.path.dirname(dst) or "/app/tmp_files"
    os.makedirs(out_dir, exist_ok=True)
    subprocess.run(["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", out_dir, src], capture_output=True, timeout=180)
    gen = os.path.join(out_dir, os.path.splitext(os.path.basename(src))[0] + ".pdf")
    if os.path.exists(gen) and gen != dst:
        os.rename(gen, dst)
    return dst

def image_to_pdf(src, dst):
    import img2pdf
    with open(dst, "wb") as f:
        f.write(img2pdf.convert(src))
    return dst

def pdf_to_images(src, out_dir):
    from pdf2image import convert_from_path
    pages = convert_from_path(src)
    out = []
    for i, page in enumerate(pages):
        p = os.path.join(out_dir, f"page_{i+1}.jpg")
        page.save(p, "JPEG")
        out.append(p)
    return out

def check_code(path):
    import subprocess
    r = subprocess.run(["pyflakes", path], capture_output=True, text=True)
    return r.stdout + r.stderr or "Ошибок не найдено."
