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
| News sites | ✅ Works (api+selenium) |
| Twitter/X | ✅ Works in browser (selenium) |
| Instagram | ✅ Works in browser (selenium) |
| Facebook | ✅ Works (selenium) |
| bit.ly / short URLs | ✅ Auto-expands |


For Twitter/X/Instagram/Facebook, we'll add nodriver support in Phase 2.
