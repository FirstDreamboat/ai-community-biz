# -*- coding: utf-8 -*-
import re
import html

content = open('c:/Users/admin/Desktop/AI-Community-biz-mine/unpacked_scheme/word/document.xml', encoding='utf-8').read()
text = re.sub(r'<w:p[ >]', '\n', content)
text = re.sub(r'<[^>]+>', '', text)
text = html.unescape(text)
text = re.sub(r'w14:paraId="[0-9A-F]+">', '', text)
# 清理多余空行
lines = [l.strip() for l in text.split('\n')]
lines = [l for l in lines if l]
out = '\n'.join(lines)
open('c:/Users/admin/Desktop/AI-Community-biz-mine/方案书提取.txt', 'w', encoding='utf-8').write(out)
print('done', len(out))
