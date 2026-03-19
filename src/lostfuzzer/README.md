# Automated URL Recon & DAST Scanning

## FROM
https://github.com/coffinxp/lostfuzzer

## Overview
This script automates the process of extracting, filtering, and testing passive URLs by using **gau** tool. It checks for live URLs and performs **DAST (Dynamic Application Security Testing)** using **nuclei**.

## 🚀 Why This Tool?

ParamSpider can create **imbalanced URLs** like:  
```
http://testphp.vulnweb.com/listproducts.php?artist=FUZZ&cat=FUZZ
```
This breaks **Nuclei DAST** scans because every query needs a valid parameter. The URL has too many FUZZ placeholders. This makes it harder for Nuclei to properly process and test each parameter because valid query structures are needed for effective scanning.also i did'nt used any active crawler tool bcz thats takes lots of time to get live urls from targets.

That’s why I built this custom tool to extract only valid URLs with full query parameters, ensuring they are correctly formatted for security testing.

### 🛠️ What This Tool Does:  
✅ **Extracts valid URLs** with real query parameters  
✅ **Removes imbalanced/fuzzed queries**  
✅ **Checks live URLs** before scanning  
✅ **Runs Nuclei DAST properly** for accurate results  

This makes **bug hunting faster, cleaner, and more effective!** 🚀

## Prerequisites
Ensure the following tools are installed before running the script:

- [`gau`](https://github.com/lc/gau)
- [`uro`](https://github.com/s0md3v/uro)
- [`nuclei`](https://github.com/projectdiscovery/nuclei)
- [`httpx-toolkit`](https://github.com/projectdiscovery/httpx)

## Installation
Clone the repository and navigate into it:
```bash
git clone https://github.com/coffinxp/lostfuzzer.git
cd lostfuzzer
```
Make the script executable:
```bash
chmod +x lostfuzzer.sh
```

## Usage
Run the script and follow the prompts:
```bash
./lostfuzzer.sh
```
You'll be asked to provide:
- A **target domain** or a **file** containing a list of subdomains

The script will:
1. Fetch passive URLs by **gau** tool in parallel if there are multiple subdomains
2. Filter URLs containing query parameters
3. Check which URLs are live using **httpx-toolkit**
4. Run **nuclei** for **DAST scanning**
5. Save results for manual testing

## Output Files
- `filtered_urls.txt`: Filtered URLs with query parameters for further manual testing
- `nuclei_results.txt`: Results of the DAST scan

## Example Output
![Screenshot (1207)](https://github.com/user-attachments/assets/d663b424-2a89-4439-b54e-ba54e7397e21)

## Disclaimer
This tool is intended for **educational and legal security testing purposes only**. The author is not responsible for any misuse of this script.
