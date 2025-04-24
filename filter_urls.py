import json
import os

# Path to the wiki_urls.json file
file_path = os.path.join('data', 'wiki_urls.json')

# Read the current file
with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Count the original URLs
original_count = len(data)

# Filter out URLs containing 'Interactive+Map' (case insensitive), 
# URLs ending with .png or .gif, and URLs containing 'png?v'
filtered_data = {}
for url, value in data.items():
    if ('interactive+map' not in url.lower() and 
        'shadow+of+the+erdtree+map' not in url.lower() and
        not url.lower().endswith('.png') and 
        not url.lower().endswith('.gif') and
        'png?v=' not in url.lower()):
        filtered_data[url] = value

# Count the remaining URLs
new_count = len(filtered_data)
removed_count = original_count - new_count

# Write the filtered data back to the file
with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(filtered_data, f, indent=2)

print(f'Original URLs: {original_count}')
print(f'URLs after filtering: {new_count}')
print(f'Removed {removed_count} URLs:')
print(f' - URLs containing "Interactive+Map"')
print(f' - URLs ending with ".png" or ".gif"')
print(f' - URLs containing "png?v="')