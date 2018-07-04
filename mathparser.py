from collections import namedtuple

MathOp = namedtuple('MathOp', ['precedence', 'associativity', 'function'])
ops = {
	'+': MathOp(2, 'Left', lambda a,b: a+b),
	'-': MathOp(2, 'Left', lambda a,b: a-b),
	'*': MathOp(3, 'Left', lambda a,b: a*b),
	'/': MathOp(3, 'Left', lambda a,b: a/b),
	'(': MathOp(0, 'Left', None),
	')': MathOp(9, 'Left', None),
	'^': MathOp(4, 'Right', lambda a,b: a**b)
}

def tokenize(x):
	buff = []
	out = []
	x = x.replace(" ","")
	for token in x:
		if token in ops:
			if buff:
				try:
					out.append(float(''.join(buff)))
				except ValueError:
					out.append(''.join(buff))
			buff = []
			out.append(token)
		else:
			buff.append(token)
	if buff:
		out.append(''.join(buff))
	return out

def has_precedence(a, b):
	return (a.precedence > b.precedence) or ((a.precedence == b.precedence) and b.associativity=='Left')

def rpn(tokens):
	rpn_output = []
	stack = []
	for token in tokens:
		if token == '(':
			stack.append(token)
		elif token == ')':
			while stack:
				a = stack.pop()
				if a != '(':
					rpn_output.append(a)
				else: 
					break
		elif token in ops:
			if not stack:
				stack.append(token)
			else:
				while stack and has_precedence(ops[stack[-1]], ops[token]):
					rpn_output.append(stack.pop())
				stack.append(token)
		else:
			rpn_output.append(token)
	while stack:
		rpn_output.append(stack.pop())
	return rpn_output

class mathExpression(object):
	def __init__(self, expr):
		self.expr = expr
		tokens = tokenize(expr)
		self.exprRPN = rpn(tokenize(expr))

	def eval_rpn(self, variables=None):
		stack = []
		postfix = self.exprRPN
		for token in postfix:
			if token in ops:
				b = stack.pop()
				a = stack.pop()
				if isinstance(a, str):
					a = variables[a]
				if isinstance(b, str):
					b = variables[b]
				res = ops[token].function(a, b)
				stack.append(res)
			else:
				if isinstance(token, str):
					token = variables[token]
				stack.append(token)
		return stack.pop()