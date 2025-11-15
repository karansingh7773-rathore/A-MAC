# 📄 Document Reading Capability - Complete Guide

## Overview

Your AI agent can now **read and extract text from virtually any document type**! This includes PDFs, Word documents, PowerPoint presentations, Excel files, text files, and even scanned images.

## 🚀 What Can It Do?

### Supported File Types

- **📕 PDF Files** (.pdf) - Digital and scanned
- **📝 Word Documents** (.docx)
- **📊 PowerPoint Presentations** (.pptx)
- **📈 Excel Spreadsheets** (.xlsx)
- **📄 Text Files** (.txt)
- **🖼️ Images** (.jpg, .png, .bmp, .tiff) - with OCR
- **🌐 HTML Files** (.html)
- **📧 Email Files** (.eml, .msg)
- And many more!

### Key Features

1. **Auto-Detection** - Automatically figures out file type
2. **OCR Support** - Reads text from scanned documents and images using Tesseract
3. **Structure Recognition** - Identifies:
   - Titles and headings
   - Paragraphs
   - Lists
   - Tables
   - Other elements
4. **Intelligent Cleaning** - Removes headers, footers, and page numbers
5. **Multi-format** - Handles both digital and scanned documents

## 📝 How to Use

### Via Telegram

Simply ask your agent to read a document:

```
User: Read the PDF at D:/Documents/contract.pdf

Agent: [Calls read_document tool and returns formatted content]
```

### Example Requests

#### 1. Reading a PDF
```
You: "Read the report.pdf on my desktop"
Agent: "What's the full path to your desktop? For example: C:/Users/YourName/Desktop/report.pdf"
You: "C:/Users/John/Desktop/report.pdf"
Agent: [Extracts and displays content with titles, headings, and text]
```

#### 2. Extracting Text from Scanned Document
```
You: "Extract text from the scanned invoice at E:/Work/invoice_scan.jpg"
Agent: [Performs OCR and returns extracted text]
```

#### 3. Reading PowerPoint Presentation
```
You: "What does the presentation.pptx say?"
Agent: "What's the complete file path to presentation.pptx?"
You: "D:/Downloads/meeting_slides.pptx"
Agent: [Extracts all slide content including titles and text]
```

#### 4. Reading Word Document
```
You: "Read this contract at C:/Legal/contract_v2.docx"
Agent: [Extracts formatted content with headings and paragraphs]
```

## 🔧 Technical Details

### Under the Hood

The agent uses the **Unstructured** library, which:

1. **Detects File Type** - Automatically identifies the document format
2. **Partitions Content** - Breaks document into logical elements
3. **Applies OCR** - Uses Tesseract for scanned documents
4. **Structures Output** - Organizes content by element type
5. **Cleans Data** - Removes unnecessary elements

### Output Format

The tool returns structured content like this:

```
📄 Document: contract.pdf
📊 Size: 245.67 KB
📝 Elements found: 42

============================================================

📌 TITLES:
  • Service Agreement Contract

📑 HEADINGS:
  • Terms and Conditions
  • Payment Schedule
  • Termination Clause

📖 CONTENT:
This agreement is entered into on November 12, 2025...
[Full paragraphs of text]

📋 LISTS:
  • Payment due within 30 days
  • All modifications must be in writing
  • Either party may terminate with 60 days notice

📊 TABLES:
[Table content if present]
```

## ⚙️ Installation

The required libraries are already installed:

```bash
pip install unstructured[all-docs] pytesseract python-magic-bin pdf2image python-docx python-pptx openpyxl pandas
```

### Dependencies

- **Unstructured** - Main document processing library
- **Tesseract OCR** - For scanned documents (included in python-magic-bin)
- **PDF Processing** - pdf2image, pikepdf
- **Office Documents** - python-docx, python-pptx, openpyxl
- **Data Analysis** - pandas for structured data

## 🎯 Best Practices

### 1. Always Use Absolute Paths

✅ **Good:**
```
D:/Documents/report.pdf
C:/Users/John/Desktop/invoice.docx
E:/Work/presentation.pptx
```

❌ **Bad:**
```
report.pdf (relative path)
../Documents/file.pdf (relative path)
~/Desktop/file.pdf (home directory shortcut - won't work on Windows)
```

### 2. File Path Format

On Windows, use either:
- Forward slashes: `D:/Documents/file.pdf`
- Escaped backslashes: `D:\\Documents\\file.pdf`

### 3. Handling Large Documents

For very large documents (100+ pages):
- The tool will extract all content
- Processing may take a few seconds
- OCR on scanned documents is slower than digital PDFs

### 4. OCR Quality

For best OCR results:
- Use high-resolution scans (300 DPI or higher)
- Ensure text is clear and not too small
- Good lighting/contrast in scanned images

## 🧪 Testing

Use the test script to verify functionality:

```bash
python test_document_reading.py
```

Then provide a file path when prompted.

## 🔍 Troubleshooting

### "File not found" Error

**Problem:** The file path is incorrect or file doesn't exist

**Solution:** 
- Verify the file exists at that location
- Use Windows Explorer to copy the full path
- Make sure you're using absolute paths

### "No content could be extracted"

**Problem:** File is corrupted or in an unsupported format

**Solution:**
- Try opening the file manually to verify it works
- Check if file is password-protected
- Verify file extension matches actual file type

### OCR Not Working

**Problem:** Scanned documents return empty or garbled text

**Solution:**
- Check image quality (should be clear and high-resolution)
- Verify Tesseract is properly installed
- Try converting image to higher resolution

## 📚 Integration with Agent

The `read_document` tool is automatically available to your agent. When a user asks to read a file, the agent will:

1. **Ask for full path** (if not provided)
2. **Call read_document** with the file path
3. **Return formatted content** organized by element type
4. **Answer questions** about the document content

### Example Workflow

```
User: "Read the contract and tell me the payment terms"

Agent's Internal Process:
1. [Calls read_document("D:/Legal/contract.pdf")]
2. [Receives structured content with headings and text]
3. [Analyzes the "Payment Schedule" section]
4. [Responds with payment terms from the document]

Agent: "According to the contract, payment terms are:
- 50% upfront upon signing
- 25% at project midpoint
- 25% upon completion
All payments due within 30 days of invoice."
```

## 🎉 Use Cases

### Business
- Extract terms from contracts
- Read invoices and receipts
- Analyze reports and presentations
- Process legal documents

### Education
- Read research papers
- Extract notes from PDFs
- Analyze study materials
- Process assignments

### Personal
- Read scanned letters
- Extract text from images
- Process tax documents
- Read ebooks and articles

## 🔐 Privacy & Security

- **Local Processing** - All document processing happens on your server
- **No Cloud Upload** - Documents are not sent to external services (except for AI analysis)
- **Temporary Storage** - No permanent copies are stored
- **User Data** - Only the text content is extracted and processed

## 📊 Performance

| File Type | Size | Processing Time |
|-----------|------|-----------------|
| Digital PDF | 1 MB | ~2-3 seconds |
| Scanned PDF | 5 MB | ~10-15 seconds |
| DOCX | 500 KB | ~1-2 seconds |
| PPTX | 2 MB | ~3-5 seconds |
| Image (OCR) | 2 MB | ~5-8 seconds |

*Times vary based on document complexity and system resources*

## 🚀 Advanced Usage

### Combining with Other Tools

You can combine document reading with other agent capabilities:

```
User: "Read the report.pdf and email a summary to my boss"

Agent Process:
1. read_document("D:/Reports/report.pdf")
2. Analyze content and create summary
3. get_user_history to find boss's email
4. send_email with the summary
```

### Batch Processing

```
User: "Read all PDFs in D:/Contracts/ and tell me which ones expire this month"

Agent: [Would need to list directory first, then read each PDF and analyze dates]
```

## 📖 API Reference

### read_document(file_path: str) -> str

**Parameters:**
- `file_path` (str): Absolute path to the document file

**Returns:**
- Formatted string with structured document content

**Raises:**
- Error if file not found
- Error if file is not accessible
- Error if file format is not supported

## 🆕 What's New

- **v1.0** - Initial release with PDF, DOCX, PPTX, images support
- OCR capability using Tesseract
- Structured output with element categorization
- Auto file type detection

## 🤝 Contributing

To add support for new file types, edit the `read_document` function in `tools.py` and update the Unstructured library configuration.

---

**Built with:**
- [Unstructured](https://github.com/Unstructured-IO/unstructured) - Document processing
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) - Text recognition
- [Pillow](https://python-pillow.org/) - Image processing
- [python-docx](https://python-docx.readthedocs.io/) - Word documents
- [python-pptx](https://python-pptx.readthedocs.io/) - PowerPoint files
