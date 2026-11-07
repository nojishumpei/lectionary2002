-- Book-only row layout after Gregorio has engraved each unchanged score.
-- The only Gregorio-specific marker used here identifies the staff-line box.
local M = {}
local H, V = node.id('hlist'), node.id('vlist')
local RULE, GLUE, KERN = node.id('rule'), node.id('glue'), node.id('kern')
local PENALTY = node.id('penalty')
local part = assert(luatexbase.attributes['gre@attr@part'])

-- Coordinates are in scaled points, positive downwards, relative to the
-- enclosing line's baseline. In vertical lists, box shifts are horizontal.
local function staff_top(box, baseline)
  local vertical = box.id == V
  local y = vertical and (baseline - box.height) or baseline
  for child in node.traverse(box.head) do
    if child.id == H or child.id == V then
      local child_baseline = vertical and (y + child.height)
        or (baseline + child.shift)
      if node.has_attribute(child, part, 2) then
        local top = child_baseline - child.height
        for item in node.traverse(child.head) do
          if item.id == RULE then return top end
          if item.id == GLUE then top = top + node.effective_glue(item, child)
          elseif item.id == KERN then top = top + item.kern
          elseif item.id == H or item.id == V then
            top = top + item.height + item.depth
          end
        end
      end
      local found = staff_top(child, child_baseline)
      if found then return found end
      if vertical then y = y + child.height + child.depth end
    elseif vertical then
      if child.id == GLUE then y = y + node.effective_glue(child, box)
      elseif child.id == KERN then y = y + child.kern
      elseif child.id == RULE then y = y + child.height + child.depth end
    end
  end
end

function M.normalize(register, step, staff_offset)
  local box = tex.box[register]
  local original = box.head
  box.head = nil
  local first, last, count, pending_penalty = nil, nil, 0, 0
  local function append(item)
    item.prev, item.next = last, nil
    if last then last.next = item else first = item end
    last = item
  end
  local current = original
  while current do
    local following = current.next
    current.prev, current.next = nil, nil
    local anchor = current.id == H and staff_top(current, 0)
    if anchor then
      if count > 0 then
        local p = node.new(PENALTY)
        p.penalty = pending_penalty
        append(p)
      end
      local baseline = staff_offset - anchor
      local top = baseline - current.height
      local bottom = baseline + current.depth
      texio.write_nl('log', string.format(
        'BOOK-GRID-ROW: top=%.3fpt; bottom=%.3fpt; staff=%.3fpt',
        top / 65536, bottom / 65536, staff_offset / 65536))
      if top < -65536 or bottom > step + 65536 then
        tex.error('Chant line exceeds its book grid row', {
          string.format('Top %.3fpt, bottom %.3fpt; row is %.3fpt.',
            top / 65536, bottom / 65536, step / 65536),
          'Increase the grid step or adjust the common staff offset.'})
      end
      local leading = node.new(KERN)
      leading.kern, leading.next, current.prev = top, current, leading
      local trailing = node.new(KERN)
      trailing.kern, trailing.prev, current.next = step - bottom, current, trailing
      local row = node.new(V)
      row.head, row.width, row.height, row.depth = leading, current.width, step, 0
      row.dir = current.dir
      append(row)
      count, pending_penalty = count + 1, 0
    elseif current.id == PENALTY then
      pending_penalty = current.penalty
      node.free(current)
    elseif current.id == GLUE or current.id == KERN then
      node.free(current)
    else
      -- Keep writes and other nonspacing material in its original order.
      append(current)
    end
    current = following
  end
  assert(count > 0, 'No Gregorio staff lines found in score')
  box.head, box.height, box.depth = first, count * step, 0
  return count
end

return M
