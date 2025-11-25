# Define the output filename
$outputFile = "giant_all_programs.txt"

# Check if the output file already exists and delete it to start fresh
if (Test-Path $outputFile) {
    Remove-Item $outputFile
}

# Get all .html files in the current folder and sort them by name
$files = Get-ChildItem -Filter *.html | Sort-Object Name

# Initialize the counter
$i = 1

# Loop through each file found
foreach ($file in $files) {
    Write-Host "Processing $($file.Name)..."

    # Read the content of the HTML file
    # -Raw reads it as one single string rather than an array of lines
    $content = Get-Content -Path $file.FullName -Raw

    # Append the HTML content to the output file
    Add-Content -Path $outputFile -Value $content

    # Create the label and separator block
    # `r`n creates a new line
    $separator = "`r`nPROGRAM $i`r`n___________________________________________________`r`n"

    # Append the label/separator to the output file
    Add-Content -Path $outputFile -Value $separator

    # Increment the counter
    $i++
}

Write-Host "Success! All files parsed into $outputFile"