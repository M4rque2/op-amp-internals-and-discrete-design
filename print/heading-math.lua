-- XeLaTeX/ctex cannot safely place unicode-math alphabet commands in every
-- moving argument used for headings, bookmarks, and the table of contents.
-- Keep body equations as real mathematics, but use a compact textual form for
-- the handful of symbols that occur inside Markdown headings.

local greek = {
  alpha = "α",
  beta = "β",
  gamma = "γ",
  delta = "δ",
  epsilon = "ε",
  lambda = "λ",
  mu = "μ",
  pi = "π",
  tau = "τ",
  omega = "ω",
}

local function is_text_codepoint(codepoint)
  return
    (codepoint >= 0x2E80 and codepoint <= 0x303F) or -- CJK punctuation/radicals
    (codepoint >= 0x3040 and codepoint <= 0x30FF) or -- Japanese kana
    (codepoint >= 0x3400 and codepoint <= 0x4DBF) or -- CJK Extension A
    (codepoint >= 0x4E00 and codepoint <= 0x9FFF) or -- CJK Unified Ideographs
    (codepoint >= 0xF900 and codepoint <= 0xFAFF) or -- CJK compatibility
    (codepoint >= 0xFF00 and codepoint <= 0xFFEF) or -- full-width forms
    codepoint == 0x2103                            -- degree Celsius
end

local function wrap_cjk_in_text(math)
  -- Force Greek unit/variable glyphs to come from the Unicode math font.
  -- Otherwise unicode-math can ask the surrounding Times text font for the
  -- mathematical-alphanumeric codepoints in captions and other text contexts.
  math.text = math.text:gsub("\\Omega", "\\symup{Ω}")
  math.text = math.text:gsub("_%s*\\mu", "_{\\symit{μ}}")
  math.text = math.text:gsub("%^%s*\\mu", "^{\\symit{μ}}")
  math.text = math.text:gsub("\\mu", "\\symit{μ}")

  local output = {}
  local text_run = {}

  local function flush_text_run()
    if #text_run > 0 then
      output[#output + 1] = "\\text{" .. table.concat(text_run) .. "}"
      text_run = {}
    end
  end

  for _, codepoint in utf8.codes(math.text) do
    local character = utf8.char(codepoint)
    if is_text_codepoint(codepoint) then
      text_run[#text_run + 1] = character
    else
      flush_text_run()
      output[#output + 1] = character
    end
  end
  flush_text_run()

  math.text = table.concat(output)
  return math
end

local function heading_math_to_text(math)
  local value = math.text

  value = value:gsub("\\mathrm%s*{(.-)}", "%1")
  value = value:gsub("\\text%s*{(.-)}", "%1")

  for command, character in pairs(greek) do
    value = value:gsub("\\" .. command, character)
  end

  value = value:gsub("[{}]", "")
  value = value:gsub("%s+", " ")
  return pandoc.Str(value)
end

function Header(header)
  header.content = header.content:walk({ Math = heading_math_to_text })
  local title = pandoc.utils.stringify(header.content)
  local chapter_number = title:match("^第%s*(%d+)%s*章")

  if FORMAT:match("latex") and chapter_number then
    local title_latex = pandoc.write(
      pandoc.Pandoc({ pandoc.Plain(header.content) }),
      "latex"
    ):gsub("%s+$", "")
    local opening = string.format(
      [[\cleardoublepage
\thispagestyle{empty}
\phantomsection
\hypertarget{book-chapter-%s}{}
\addcontentsline{toc}{section}{%s}
\null\vfill
{\centering\LARGE\bfseries %s\par}
\vfill\null
\clearpage]],
      chapter_number,
      title_latex,
      title_latex
    )
    return pandoc.RawBlock("latex", opening)
  end

  if FORMAT:match("latex") and header.level == 1 then
    return {
      pandoc.RawBlock(
        "latex",
        "\\cleardoublepage\\thispagestyle{plain}"
      ),
      header,
    }
  end
  return header
end

function Math(math)
  return wrap_cjk_in_text(math)
end
