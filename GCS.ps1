[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string[]]$Target,

    [string]$Property,
    [string]$Url,

    [string]$Wrapper = "C:\Users\JDSDirectLLC\.codex\skills\gcs\scripts\gcs-url-inspection.ps1",
    [switch]$Raw
)

$ErrorActionPreference = "Stop"

$defaultTargets = @(
    "https://academai.app/",
    "https://www.digitalenergyholdings.com/",
    "https://stl-musicians.com/",
    "https://www.coldstonesoap.com/",
    "https://www.stlouiscreations.com/",
    "https://www.digitalenergymedia.com/"
)

if (-not (Test-Path -LiteralPath $Wrapper -PathType Leaf)) {
    throw "GCS wrapper was not found: $Wrapper"
}

function Invoke-GcsInspection {
    param(
        [string]$TargetValue,
        [string]$PropertyValue,
        [string]$UrlValue
    )

    if ($PropertyValue -or $UrlValue) {
        if (-not $PropertyValue -or -not $UrlValue) {
            throw "Use both -Property and -Url together, or pass URL/domain targets."
        }

        return & powershell -NoProfile -ExecutionPolicy Bypass -File $Wrapper -Property $PropertyValue -Url $UrlValue
    }

    return & powershell -NoProfile -ExecutionPolicy Bypass -File $Wrapper $TargetValue
}

function Get-ShortCoverage {
    param([string]$Coverage)

    switch -Wildcard ($Coverage) {
        "Submitted and indexed" { return "Indexed" }
        "Page with redirect" { return "Redirect" }
        "Alternate page with proper canonical tag" { return "Canonical" }
        "URL is unknown to Google" { return "Unknown" }
        default { return $Coverage }
    }
}

function Get-ShortHost {
    param([string]$Value)

    if (-not $Value) {
        return ""
    }

    try {
        $uri = [Uri]$Value
        return $uri.Host
    }
    catch {
        return $Value
    }
}

if ($Property -or $Url) {
    $targetsToInspect = @($Url)
}
elseif ($Target -and $Target.Count -gt 0) {
    $targetsToInspect = $Target
}
else {
    $targetsToInspect = $defaultTargets
}

$results = foreach ($targetValue in $targetsToInspect) {
    Write-Host "Inspecting $targetValue" -ForegroundColor Cyan

    try {
        $rawJson = Invoke-GcsInspection -TargetValue $targetValue -PropertyValue $Property -UrlValue $Url

        if ($Raw) {
            $rawJson
            continue
        }

        $data = ($rawJson -join "`n") | ConvertFrom-Json
        $index = $data.inspectionResult.indexStatusResult

        [pscustomobject]@{
            Site = Get-ShortHost -Value $targetValue
            Verdict = $index.verdict
            Status = Get-ShortCoverage -Coverage $index.coverageState
            LastCrawl = $index.lastCrawlTime
            Canonical = Get-ShortHost -Value $index.googleCanonical
        }
    }
    catch {
        [pscustomobject]@{
            Site = Get-ShortHost -Value $targetValue
            Verdict = "ERROR"
            Status = $_.Exception.Message
            LastCrawl = ""
            Canonical = ""
        }
    }
}

if (-not $Raw) {
    $results | Format-Table -AutoSize -Wrap

    if ($results | Where-Object { $_.Verdict -eq "ERROR" }) {
        exit 1
    }
}
