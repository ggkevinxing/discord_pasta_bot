import pathlib
src = pathlib.Path('src/utils/log_util.py').read_text()
NL = chr(10)
BS = chr(92)
# Fix #1: prior heredoc delivery left a literal newline inside what should be
# Python source for `text = text.replace("\n", ...)[:237] + "..."`. Build the
# broken and fixed byte sequences explicitly via chr() so the string-to-source
# replacement is unambiguous.
broken = "        text = text.replace(" + NL
fixed = '        text = text.replace("' + BS + 'n' + '", " ")[:237] + "..."' + NL
assert broken in src, "broken fragment not found"
src = src.replace(broken, fixed)
# Fix #2: narrow header_value's catch-all except to specific exceptions so
# real bugs aren't silently swallowed.
b2 = "    except Exception:" + NL + "        return None"
f2 = "    except (KeyError, TypeError, AttributeError):" + NL + "        return None"
assert b2 in src, "header_value except fragment not found"
src = src.replace(b2, f2)
pathlib.Path('src/utils/log_util.py').write_text(src)
print("FIXED")
