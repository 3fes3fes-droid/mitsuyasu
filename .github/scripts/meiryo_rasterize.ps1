Add-Type -AssemblyName System.Drawing

$families = [System.Drawing.FontFamily]::Families | ForEach-Object { $_.Name }
if ($families -notcontains 'Meiryo') {
  Write-Host 'Installed fonts containing Meiryo:'
  $families | Where-Object { $_ -match 'Meiryo|メイリオ' } | ForEach-Object { Write-Host $_ }
  throw 'Meiryo font is not installed on this Windows runner.'
}

$path = 'izuni.html'
$html = Get-Content $path -Raw -Encoding UTF8
$html = $html -replace '<link href="https://fonts.googleapis.com/css2\?family=BIZ\+UDPGothic:wght@700&family=Roboto\+Condensed:wght@700&display=swap" rel="stylesheet">', '<link href="https://fonts.googleapis.com/css2?family=Roboto+Condensed:wght@700&display=swap" rel="stylesheet">'
$html = $html -replace 'font-family:"BIZ UDPGothic",Meiryo,"Yu Gothic",sans-serif', 'font-family:Meiryo,"Yu Gothic",sans-serif'

$set = New-Object 'System.Collections.Generic.HashSet[char]'
foreach ($m in [regex]::Matches($html, '[ぁ-んァ-ヶ一-龯々ー・／（）→←]')) { [void]$set.Add($m.Value[0]) }
for ($i=33; $i -le 126; $i++) { [void]$set.Add([char]$i) }
foreach ($c in @('　','→','←','／','・','（','）','ー')) { [void]$set.Add([char]$c) }

$font = New-Object System.Drawing.Font('Meiryo', 88, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
$fmt = New-Object System.Drawing.StringFormat([System.Drawing.StringFormat]::GenericTypographic)
$fmt.FormatFlags = $fmt.FormatFlags -bor [System.Drawing.StringFormatFlags]::MeasureTrailingSpaces
$probe = New-Object System.Drawing.Bitmap(4,4)
$pg = [System.Drawing.Graphics]::FromImage($probe)
$pg.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit

$em = $font.FontFamily.GetEmHeight($font.Style)
$asc = $font.FontFamily.GetCellAscent($font.Style)
$desc = $font.FontFamily.GetCellDescent($font.Style)
$ascentPx = $font.Size * $asc / $em
$descentPx = $font.Size * $desc / $em
$H = 112
$baseline = ($H - ($ascentPx + $descentPx)) / 2 + $ascentPx
$originY = $baseline - $ascentPx

$map = [ordered]@{}
foreach ($ch in ($set | Sort-Object)) {
  $txt = [string]$ch
  $size = $pg.MeasureString($txt, $font, 1000, $fmt)
  $W = [Math]::Max(18, [Math]::Ceiling($size.Width) + 8)
  $bmp = New-Object System.Drawing.Bitmap($W,$H,[System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.Clear([System.Drawing.Color]::Transparent)
  $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
  $brush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::White)
  $g.DrawString($txt,$font,$brush,4,$originY,$fmt)
  $ms = New-Object System.IO.MemoryStream
  $bmp.Save($ms,[System.Drawing.Imaging.ImageFormat]::Png)
  $b64 = [Convert]::ToBase64String($ms.ToArray())
  $map[$txt] = [ordered]@{ d = "data:image/png;base64,$b64"; w = [Math]::Round($W / $H,4) }
  $ms.Dispose(); $brush.Dispose(); $g.Dispose(); $bmp.Dispose()
}
$pg.Dispose(); $probe.Dispose(); $font.Dispose(); $fmt.Dispose()

$json = $map | ConvertTo-Json -Compress -Depth 4
$template = Get-Content '.github/scripts/meiryo_runtime.template.js' -Raw -Encoding UTF8
$runtime = $template.Replace('__MEIRYO_MAP__',$json)
$replacement = "<script>`n$runtime`n</script>`n`n</body>"
$pattern = '(?s)<script>\s*\(\(\)=>\{\s*const SKIP=.*?</script>\s*</body>'
if (-not [regex]::IsMatch($html,$pattern)) { throw 'Existing image-text script block was not found.' }
$html = [regex]::Replace($html,$pattern,[System.Text.RegularExpressions.MatchEvaluator]{ param($m) $replacement },1)
[System.IO.File]::WriteAllText((Resolve-Path $path),$html,(New-Object System.Text.UTF8Encoding($false)))
