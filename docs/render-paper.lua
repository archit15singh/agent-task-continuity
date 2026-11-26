-- Keep repository links usable when the PDF is read outside the checkout.
local repository = "https://github.com/archit15singh/agent-task-continuity/blob/"
local study = "b289080180e4f8b5e9b93d9b6d70b62fb17831d4"

function Link(link)
  local target = link.target
  if target:match("^%.%./evidence/") then
    local path = target:sub(4)
    local revision = study
    if path:match("^evidence/README%.md") or path == "evidence/reporting-verification.json" then
      revision = "main"
    end
    link.target = repository .. revision .. "/" .. path
  elseif target:match("^[%w%-]+%.md$") then
    link.target = repository .. "main/docs/" .. target
  end
  return link
end
