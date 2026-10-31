/**
 * Formats draft text to ensure clean spacing, proper newlines, numbered checklist items,
 * and distinct section headers.
 */
export function formatDraftText(raw: string): string {
  if (!raw) return "";
  let text = raw;

  // 1. Separate checklist checkboxes [ ] if preceded by non-newline
  text = text.replace(/([^\n])\s*(\[[ xX]\])/g, "$1\n\n$2");

  // 2. Separate section headers
  const headers = [
    "PATIENT & ADMISSION DETAILS:",
    "INCONSISTENCIES TO BE VERIFIED:",
    "ACTION SUMMARY:",
    "STATUTORY BASIS IN PUBLISHED RULES:",
    "REQUEST:",
    "What appears inconsistent \\(to be verified\\):",
    "Summary:",
    "Basis in published rules:",
    "Request:",
    "Ranking:",
    "Note:",
  ];
  for (const h of headers) {
    text = text.replace(new RegExp(`([^\\n])\\s*(${h})`, "g"), "$1\n\n$2");
  }

  // 3. Separate rule bullets and item bullets
  text = text.replace(/([^\n])\s*(-\s+[A-Z0-9_\-]+:)/g, "$1\n$2");

  // 4. Separate disclaimers
  text = text.replace(
    /([^\n])\s*(This checklist is prepared by RELIEF)/g,
    "$1\n\n--------------------------------------------------------------------------------\n$2"
  );
  text = text.replace(
    /([^\n])\s*(Notes for the facilitator before sending)/g,
    "$1\n\n--------------------------------------------------------------------------------\n$2"
  );

  // 5. Clean up numbered checklist items
  const lines = text.split("\n");
  const newLines: string[] = [];
  let itemIdx = 1;
  let inItems = false;
  for (const line of lines) {
    const stripped = line.trim();
    if (stripped.startsWith("Items to complete or confirm:")) {
      inItems = true;
      newLines.push(line);
      newLines.push("");
      continue;
    }
    if (inItems && (stripped.startsWith("This checklist") || stripped.startsWith("---"))) {
      inItems = false;
      newLines.push(line);
      continue;
    }
    if (inItems && stripped.startsWith("[ ]")) {
      const content = stripped.slice(3).trim();
      if (!/^\d+\./.test(content)) {
        newLines.push(`[ ] ${itemIdx}. ${content}`);
        newLines.push("");
        itemIdx++;
      } else {
        newLines.push(stripped);
        newLines.push("");
      }
    } else {
      newLines.push(line);
    }
  }

  let res = newLines.join("\n");
  res = res.replace(/\n{3,}/g, "\n\n");
  return res.trim() + "\n";
}

