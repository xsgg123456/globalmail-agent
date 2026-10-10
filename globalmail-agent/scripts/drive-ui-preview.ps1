param(
  [ValidateSet('incoming', 'business_update', 'reset')][string]$Action = 'incoming',
  [string]$ConversationId = 'demo-mail-02',
  [string]$Body = '',
  [string]$OrderId = 'DEMO-1002',
  [string]$PatchJson = '{}',
  [string]$CommandId = [guid]::NewGuid().ToString()
)
$ErrorActionPreference = 'Stop'
$previewCommand = @{ type = $Action; id = $CommandId }
if ($Action -eq 'incoming') {
  if ([string]::IsNullOrWhiteSpace($Body)) { throw 'incoming requires -Body' }
  $previewCommand.conversationId = $ConversationId
  $previewCommand.body = $Body
}
if ($Action -eq 'business_update') {
  $previewCommand.orderId = $OrderId
  $previewCommand.patch = $PatchJson | ConvertFrom-Json
}
$previewPayload = [Text.Encoding]::UTF8.GetBytes(($previewCommand | ConvertTo-Json -Depth 8 -Compress))
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:15175/__ui_preview__/events' -Headers @{ 'X-Preview-Control' = 'local-script' } -ContentType 'application/json; charset=utf-8' -Body $previewPayload | ConvertTo-Json -Depth 8
