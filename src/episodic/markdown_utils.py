"""
Markdown Utilities - Parsing and formatting markdown files
"""
import re
from typing import List, Dict, Any, Optional


class MarkdownParser:
    """
    Parser for markdown documents
    """
    
    def __init__(self):
        """Initialize markdown parser"""
        self.heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        self.code_block_pattern = re.compile(r'```(\w+)?\n(.*?)```', re.DOTALL)
        self.link_pattern = re.compile(r'\[([^\]]+)\]\(([^\)]+)\)')
        self.list_pattern = re.compile(r'^[\*\-\+]\s+(.+)$', re.MULTILINE)
    
    def parse(self, markdown_text: str) -> Dict[str, Any]:
        """
        Parse markdown text into structured data
        
        Args:
            markdown_text: Markdown content
        
        Returns:
            Dict with parsed structure
        """
        return {
            'headings': self.extract_headings(markdown_text),
            'code_blocks': self.extract_code_blocks(markdown_text),
            'links': self.extract_links(markdown_text),
            'lists': self.extract_lists(markdown_text),
            'plain_text': self.strip_markdown(markdown_text)
        }
    
    def extract_headings(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract all headings with their levels
        
        Args:
            text: Markdown text
        
        Returns:
            List of headings with levels
        """
        headings = []
        for match in self.heading_pattern.finditer(text):
            level = len(match.group(1))
            content = match.group(2).strip()
            headings.append({
                'level': level,
                'content': content,
                'position': match.start()
            })
        return headings
    
    def extract_code_blocks(self, text: str) -> List[Dict[str, str]]:
        """
        Extract code blocks with language tags
        
        Args:
            text: Markdown text
        
        Returns:
            List of code blocks
        """
        code_blocks = []
        for match in self.code_block_pattern.finditer(text):
            language = match.group(1) or 'text'
            code = match.group(2).strip()
            code_blocks.append({
                'language': language,
                'code': code
            })
        return code_blocks
    
    def extract_links(self, text: str) -> List[Dict[str, str]]:
        """
        Extract all links
        
        Args:
            text: Markdown text
        
        Returns:
            List of links
        """
        links = []
        for match in self.link_pattern.finditer(text):
            links.append({
                'text': match.group(1),
                'url': match.group(2)
            })
        return links
    
    def extract_lists(self, text: str) -> List[str]:
        """
        Extract list items
        
        Args:
            text: Markdown text
        
        Returns:
            List of items
        """
        return [match.group(1).strip() for match in self.list_pattern.finditer(text)]
    
    def strip_markdown(self, text: str) -> str:
        """
        Remove markdown formatting, keep plain text
        
        Args:
            text: Markdown text
        
        Returns:
            Plain text
        """
        # Remove code blocks
        text = self.code_block_pattern.sub('', text)
        
        # Remove headings markers
        text = self.heading_pattern.sub(r'\2', text)
        
        # Remove links (keep text)
        text = self.link_pattern.sub(r'\1', text)
        
        # Remove bold/italic
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        text = re.sub(r'__(.+?)__', r'\1', text)
        text = re.sub(r'_(.+?)_', r'\1', text)
        
        # Remove inline code
        text = re.sub(r'`(.+?)`', r'\1', text)
        
        # Clean up extra whitespace
        text = re.sub(r'\n\n+', '\n\n', text)
        
        return text.strip()
    
    def get_section(self, text: str, heading: str) -> Optional[str]:
        """
        Extract content under a specific heading
        
        Args:
            text: Markdown text
            heading: Heading to search for
        
        Returns:
            Section content or None
        """
        headings = self.extract_headings(text)
        
        # Find the target heading
        target_idx = None
        target_level = None
        for i, h in enumerate(headings):
            if heading.lower() in h['content'].lower():
                target_idx = i
                target_level = h['level']
                break
        
        if target_idx is None:
            return None
        
        # Get start position
        start_pos = headings[target_idx]['position']
        
        # Find end position (next heading of same or higher level)
        end_pos = len(text)
        for i in range(target_idx + 1, len(headings)):
            if headings[i]['level'] <= target_level:
                end_pos = headings[i]['position']
                break
        
        return text[start_pos:end_pos].strip()
    
    def to_html(self, text: str) -> str:
        """
        Convert markdown to basic HTML
        
        Args:
            text: Markdown text
        
        Returns:
            HTML text
        """
        html = text
        
        # Headings
        html = re.sub(r'^######\s+(.+)$', r'<h6>\1</h6>', html, flags=re.MULTILINE)
        html = re.sub(r'^#####\s+(.+)$', r'<h5>\1</h5>', html, flags=re.MULTILINE)
        html = re.sub(r'^####\s+(.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
        html = re.sub(r'^###\s+(.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^##\s+(.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^#\s+(.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        
        # Bold
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'__(.+?)__', r'<strong>\1</strong>', html)
        
        # Italic
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        html = re.sub(r'_(.+?)_', r'<em>\1</em>', html)
        
        # Links
        html = self.link_pattern.sub(r'<a href="\2">\1</a>', html)
        
        # Code
        html = re.sub(r'`(.+?)`', r'<code>\1</code>', html)
        
        # Paragraphs
        html = re.sub(r'\n\n', '</p><p>', html)
        html = f'<p>{html}</p>'
        
        return html


class MarkdownFormatter:
    """
    Formatter for creating markdown documents
    """
    
    @staticmethod
    def heading(text: str, level: int = 1) -> str:
        """Create heading"""
        return f"{'#' * level} {text}\n\n"
    
    @staticmethod
    def bold(text: str) -> str:
        """Make text bold"""
        return f"**{text}**"
    
    @staticmethod
    def italic(text: str) -> str:
        """Make text italic"""
        return f"*{text}*"
    
    @staticmethod
    def code(text: str, inline: bool = True) -> str:
        """Format as code"""
        if inline:
            return f"`{text}`"
        return f"```\n{text}\n```\n\n"
    
    @staticmethod
    def code_block(code: str, language: str = "") -> str:
        """Create code block"""
        return f"```{language}\n{code}\n```\n\n"
    
    @staticmethod
    def link(text: str, url: str) -> str:
        """Create link"""
        return f"[{text}]({url})"
    
    @staticmethod
    def list_item(text: str, ordered: bool = False, index: int = 1) -> str:
        """Create list item"""
        if ordered:
            return f"{index}. {text}\n"
        return f"- {text}\n"
    
    @staticmethod
    def table(headers: List[str], rows: List[List[str]]) -> str:
        """Create markdown table"""
        lines = []
        
        # Headers
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        
        # Rows
        for row in rows:
            lines.append("| " + " | ".join(row) + " |")
        
        return "\n".join(lines) + "\n\n"
    
    @staticmethod
    def quote(text: str) -> str:
        """Create blockquote"""
        lines = text.split('\n')
        return "\n".join(f"> {line}" for line in lines) + "\n\n"
