# Media Monitor - Link Fetcher

Extracts text content from news articles, social media posts, and other links.

## Setup (One Time)

1. Open Terminal
2. Navigate to this folder:
   ```
   cd /path/to/media_monitor
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Option 1: Export Google Sheet as CSV

1. Open your Google Sheet
2. File → Download → CSV
3. Save as `links.csv` in this folder
4. Run:
   ```
   python fetcher.py
   ```

### Option 2: Direct from Google Sheet (coming soon)

## Output

After running, you'll get:

- `output.txt` - All extracted content
- `status.csv` - Status of each link (done / didn't open / error)

## Link Support

| Type | Status |
|------|--------|
| News sites | ✅ Works |
| Twitter/X | ⚠️ Marked "didn't open" (needs browser) |
| Instagram | ⚠️ Marked "didn't open" (needs login) |
| Facebook | ⚠️ Marked "didn't open" (needs login) |
| bit.ly / short URLs | ✅ Auto-expands |

## Troubleshooting

If newspaper3k fails on a site, the script automatically falls back to basic HTML extraction.

For Twitter/X/Instagram/Facebook, we'll add nodriver support in Phase 2.
