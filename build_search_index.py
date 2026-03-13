#!/usr/bin/env python3
"""
Build FlexSearch-compatible search index từ docs HTML.
Output: assets/search-index.json (gzipped base64 hoặc plain JSON)
Format: [{id, n, text}, ...] — id = index trong ALL array
"""
import json, os, re, sys
from html.parser import HTMLParser

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self._skip = False
        self._skip_tags = {'script', 'style', 'head'}
        self._tag_stack = []

    def handle_starttag(self, tag, attrs):
        self._tag_stack.append(tag)
        if tag in self._skip_tags:
            self._skip = True

    def handle_endtag(self, tag):
        if self._tag_stack and self._tag_stack[-1] == tag:
            self._tag_stack.pop()
        if tag in self._skip_tags:
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            stripped = data.strip()
            if stripped:
                self.text_parts.append(stripped)

    def get_text(self):
        return ' '.join(self.text_parts)


def extract_text(html_path):
    try:
        with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        parser = TextExtractor()
        parser.feed(content)
        text = parser.get_text()
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Limit to 10000 chars to keep index manageable
        return text[:10000]
    except Exception as e:
        return ''


def main():
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    index_json = os.path.join(repo_dir, 'index.json')
    
    print('Loading index.json...')
    with open(index_json) as f:
        docs = json.load(f)
    
    print(f'Building search index for {len(docs)} docs...')
    
    search_index = []
    errors = 0
    
    for i, doc in enumerate(docs):
        doc_path = os.path.join(repo_dir, 'docs', doc['p'])
        
        # Extract text from HTML
        text = ''
        if os.path.exists(doc_path):
            text = extract_text(doc_path)
        
        # Always include name in searchable text
        full_text = (doc['n'] + ' ' + text).strip()
        
        search_index.append({
            'id': i,
            'n': doc['n'],      # name (for display)
            'tx': full_text     # full searchable text
        })
        
        if (i + 1) % 100 == 0:
            print(f'  {i+1}/{len(docs)} done...')
    
    out_path = os.path.join(repo_dir, 'assets', 'search-index.json')
    print(f'Writing {out_path}...')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(search_index, f, ensure_ascii=False, separators=(',', ':'))
    
    size = os.path.getsize(out_path)
    print(f'Done! Index size: {size/1024/1024:.1f} MB ({len(search_index)} docs)')
    
    if size > 20 * 1024 * 1024:
        print('⚠️  Index > 20MB — consider reducing text limit')
    else:
        print('✅ Index size OK for client-side use')


if __name__ == '__main__':
    main()
