from pydantic import BaseModel, Field
from typing import Optional, List


class TextConfig(BaseModel):
    font_name: str = "Arial"
    font_size: int = Field(default=60, ge=8, le=400)
    font_color: str = "#FFFFFF"
    x: int = Field(default=100, ge=0)
    y: int = Field(default=100, ge=0)
    x_percent: Optional[float] = Field(default=0.5, ge=0.0, le=1.0)
    y_percent: Optional[float] = Field(default=0.5, ge=0.0, le=1.0)
    align: str = "center"  # left | center | right
    stroke_width: int = Field(default=2, ge=0, le=20)
    stroke_color: Optional[str] = "#000000"


class ContactItem(BaseModel):
    name: str
    phone: str
    original_phone: Optional[str] = None


class PreviewRequest(BaseModel):
    image_path: str
    sample_name: Optional[str] = "שם לדוגמה"
    text_config: TextConfig


class ProcessRequest(BaseModel):
    image_path: str
    contacts: List[ContactItem]
    text_config: TextConfig
    send_whatsapp: bool = True
    caption: Optional[str] = ""
    delay_seconds: float = Field(default=3.0, ge=0.0, le=60.0)
