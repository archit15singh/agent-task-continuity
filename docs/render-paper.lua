-- Keep repository links usable when the PDF is read outside the checkout.
local repository = "https://github.com/archit15singh/worktree-ledger/blob/"
local study = "b289080180e4f8b5e9b93d9b6d70b62fb17831d4"
local round_six = "07db8bc7b07469e531f6d9b960be0c561cc1e345"
local round_six_receipts = {
  ["capped-reads.json"] = true,
  ["hosted-git.json"] = true,
  ["hosted-receiver.json"] = true,
  ["operator-pilot-rehearsal.json"] = true,
  ["operator-pilot-reversed.json"] = true,
  ["receiver-qualification.json"] = true,
  ["receiver-qualification-repeat.json"] = true,
  ["scoped-click.json"] = true,
  ["scoped-click-replay.json"] = true,
}

function Link(link)
  local target = link.target
  if target:match("^%.%./evidence/") then
    local path = target:sub(4)
    local revision = study
    if path:match("^evidence/README%.md") or path == "evidence/reporting-verification.json" then
      revision = "main"
    elseif round_six_receipts[path:sub(10)] then
      revision = round_six
    end
    link.target = repository .. revision .. "/" .. path
  elseif target:match("^[%w%-]+%.md$") then
    link.target = repository .. "main/docs/" .. target
  end
  return link
end
