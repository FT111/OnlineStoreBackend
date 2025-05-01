

# Mock payment info
EBUY_IBAN = {
	'COUNTRY': 'GB',
	'BANK_CODE': 'XXXX',
	'SORT': 'XXXXXX',
	'ACCOUNT_NUMBER': 'XXXXXXXX'
}

# Suffixes for the word stemmer - In a {length: suffix[]}} format for easier editing
SUFFIXES = {
	1: ['s', 'y', 'd', 'e', ',', '+', '!', '?', '.', ':', ';', '-', '_', '(', ')', '[', ']', '{', '}', "'", '"'],
	2: ['es', 'ly', 'ed', 'ic', 'al', 'er', 'or', 'ar', 'en', 'es'],
	3: ['ing', 'ily', 'ion', 'ful', 'ism', 'ous', 'ify', 'ize', 'ise', 'ist', 'ate', 'ant', 'ent', 'pod', 'ish'],
	4: ['able', 'ible', 'ment', 'less', 'tion', 'ness', 'book', 'ship', 'ward', 'wise', 'hood', 'some',
		'like', 'ance', 'ence'],
	5: ['ation', 'ition', 'lling'],
}
# Putting the suffixes in a dictionary for quick lookup
PROCESSED_SUFFIXES = {suffix: length for length, suffixes in SUFFIXES.items() for suffix in suffixes}

# Commonly mistyped letters on a QWERTY keyboard, or letters that are often confused
COMMON_TYPO_LETTERS = {
	't': ['g', 'r', 'y', 'h'],
	'o': ['n', 'i', 'p', 'u', 'e'],
	'a': ['s', 'q', 'w', 'r', 'o', 'e', 'u'],
	's': ['a', 'd', 'z'],
	'e': ['w', 'r', 'd', 'o'],
	'i': ['o', 'u', 'y', 't', 'e'],
	'u': ['i', 'o', 'y', 'a'],
	'r': ['t', 'e', 'f'],
	'n': ['m', 'h', 'b'],
	'l': ['k', 'o', 'i'],
	'c': ['x', 'v', 'z', 'f'],
	'h': ['g', 'j', 'k', 'e'],
	'd': ['s', 'f', 'e'],
	'y': ['u', 'i', 'o'],
	'g': ['h', 'j', 'f', 't'],
	'b': ['n', 'm', 'v', 'h'],
	'q': ['w', 'e', 'a'],
	'`': ['q', 'w', 'e', 'z', 'a'],
	'k': ['j', 'l', 'o', 'i'],
	',': ['m'],
	';': ['l']
}
