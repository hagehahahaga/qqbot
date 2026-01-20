from abstract.bases.importer import PIL, io
from abstract.bases.config import CONFIG

def text2img(text: str | list[str], night: bool = False) -> bytes:
    # 处理文本输入
    if isinstance(text, str):
        lines = text.split('\n')
    else:
        lines = []
        for item in text:
            lines.extend(item.split('\n'))
    
    # 设置颜色
    if night:
        bg_color = (0, 0, 0)
        text_color = (255, 255, 255)
    else:
        bg_color = (255, 255, 255)
        text_color = (0, 0, 0)
    
    # 设置字体
    font_path = CONFIG['zh_font_path']
    font_size = 24
    font = PIL.ImageFont.truetype(font_path, font_size)
    
    # 计算文本尺寸
    line_height = font_size + 10
    max_width = 0
    for line in lines:
        if line:
            bbox = font.getbbox(line)
            line_width = bbox[2] - bbox[0]
            if line_width > max_width:
                max_width = line_width
    
    # 设置图片尺寸，添加边距
    margin = 20
    img_width = max_width + 2 * margin
    img_height = len(lines) * line_height + 2 * margin
    
    # 创建图片
    img = PIL.Image.new('RGB', (img_width, img_height), bg_color)
    draw = PIL.ImageDraw.Draw(img)
    
    # 绘制文本
    for i, line in enumerate(lines):
        if line:
            draw.text(
                (margin, margin + i * line_height),
                line,
                font=font,
                fill=text_color
            )
    
    # 保存为字节流
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return buffer.getvalue()
