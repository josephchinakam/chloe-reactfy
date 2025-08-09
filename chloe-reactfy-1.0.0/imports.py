from bs4 import BeautifulSoup
import os
import re
import json

# === Set Output Directory ===
home_dir = os.path.expanduser("~")
output_dir = os.path.join(home_dir, "Documents", "projects", "chloe-reactfy-outputs")
os.makedirs(output_dir, exist_ok=True)

# === User Input for Base Directory ===
file_path = os.path.join(home_dir, input(f"Enter directory path {home_dir}/: "))

# === Helper: Extract CSS Imports from HTML ===
def importing_css(html):
    pattern = r'<link[^>]+rel=["\']stylesheet["\'][^>]+href=["\']([^"\']+)["\'][^>]*>'
    matches = re.findall(pattern, html, re.IGNORECASE)
    return [f"import '{href.strip()}';" for href in matches]

# === Helper: Convert CSS Inline to React Style Object ===
def css_to_react_style(css_str):
    style_dict = {}
    for prop in css_str.split(';'):
        prop = prop.strip()
        if not prop or ':' not in prop:
            continue
        key, value = prop.split(':', 1)
        camel_key = key.strip().split('-')[0] + ''.join(word.capitalize() for word in key.strip().split('-')[1:])
        style_dict[camel_key] = value.strip()
    return style_dict

# === Helper: Sanitize Variable Names for Imports ===
def sanitize_var_name(name):
    name = os.path.splitext(os.path.basename(name))[0]
    return re.sub(r'\W+', '_', name)

# === HTML → JSX Conversion Core ===
def converter_core(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        html = f.read()

    soup = BeautifulSoup(html, 'html.parser')
    img_tags = soup.find_all('img')
    css_links = importing_css(html)

    imports, replacements = [], {}

    # Process Images for Import
    for i, img in enumerate(img_tags):
        if img.has_attr('src') and not img['src'].startswith('http'):
            src = img['src']
            var_name = f"{sanitize_var_name(src)}{i}"
            imports.append(f"import {var_name} from './{src}';")
            img['src'] = f"{{{var_name}}}"
            replacements[src] = var_name

    # Remove head & script tags
    if soup.head:
        soup.head.decompose()
    for script in soup.find_all('script'):
        script.decompose()

    # Process Attributes for JSX Compatibility
    for tag in soup.find_all(True):
        attrs = dict(tag.attrs)

        if 'class' in attrs:
            tag['className'] = ' '.join(attrs.pop('class'))
        if 'for' in attrs:
            tag['htmlFor'] = attrs.pop('for')
        if 'style' in attrs:
            style_jsx = '{{ ' + ', '.join(f"{k}: '{v}'" for k, v in css_to_react_style(attrs.pop('style')).items()) + ' }}'
            tag['style'] = style_jsx

        for attr in list(attrs.keys()):
            if '-' in attr and not (attr.startswith('data-') or attr.startswith('aria-')):
                parts = attr.split('-')
                camel_attr = parts[0] + ''.join(word.capitalize() for word in parts[1:])
                tag[camel_attr] = attrs.pop(attr)

    # Convert to JSX-friendly string
    html_str = str(soup)
    html_str = re.sub(r'src="\{(.+?)\}"', r'src={\1}', html_str)
    html_str = re.sub(r'<!--(.*?)-->', r'{/*\1*/}', html_str, flags=re.DOTALL)
    html_str = re.sub(r'<!DOCTYPE[^>]*>', '', html_str, flags=re.IGNORECASE)
    html_str = re.sub(r'<\/?(html|body)[^>]*>', '', html_str, flags=re.IGNORECASE)
    html_str = re.sub(r'href="[^"]*"', 'href="#"', html_str)

    return imports, html_str.strip(), css_links

# === Helper: Convert File Name to Valid React Component Name ===
def to_react_valid_name(name):
    cleaned = re.sub(r'[^a-zA-Z0-9_]', '', os.path.splitext(name)[0])
    if cleaned and cleaned[0].isdigit():
        cleaned = '_' + cleaned
    parts = re.split(r'[_\s]+', cleaned)
    return parts[0].lower() + ''.join(p.title() for p in parts[1:]) if parts else 'MyComponent'

# === Main Recursive Finder & JSX Writer ===
def global_finder(base_path):
    base_path = os.path.abspath(base_path)
    for dirpath, dirs, files in os.walk(base_path):
        # Limit search depth to 2 levels
        rel_depth = os.path.relpath(dirpath, base_path).count(os.sep)
        if rel_depth > 1:
            dirs[:] = []  # prevent descending deeper
            continue

        for file in files:
            if file.lower().endswith('.html'):
                file_full_path = os.path.join(dirpath, file)
                react_imports, modified_html, css_links = converter_core(file_full_path)
                component_name = to_react_valid_name(file)

                out_file = os.path.join(output_dir, f"{component_name}.jsx")
                with open(out_file, 'w', encoding='utf-8') as f:
                    f.write("import React from 'react';\n\n")
                    f.write("\n".join(react_imports) + "\n\n")
                    f.write("\n".join(css_links) + "\n\n")
                    f.write(f"const {component_name} = () => (\n")
                    f.write("  <>\n")
                    # Indent HTML for readability
                    formatted_html = '\n'.join("    " + line for line in modified_html.splitlines())
                    f.write(formatted_html + "\n")
                    f.write("  </>\n")
                    f.write(");\n\n")
                    f.write(f"export default {component_name};\n")
                print(f"✅ Saved JSX: {out_file}")


# === Run ===

def main():
    home_dir = os.path.expanduser("~")
    file_path = os.path.join(home_dir, input(f"Enter directory path {home_dir}/: "))
    global_finder(file_path)
    print("🎉 JSX files saved to ~/Documents/projects/chloe-reactfy-outputs/")

if __name__ == "__main__":
    main()

