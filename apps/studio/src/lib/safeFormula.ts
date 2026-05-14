type TokenType =
  | 'number'
  | 'identifier'
  | 'operator'
  | 'leftParen'
  | 'rightParen'
  | 'question'
  | 'colon'
  | 'eof'

interface Token {
  type: TokenType
  value: string
}

const MAX_FORMULA_LENGTH = 256
const MAX_TOKENS = 128
const OPERATORS = ['===', '!==', '<=', '>=', '&&', '||', '==', '!=', '+', '-', '*', '/', '%', '<', '>', '!']

function isWhitespace(char: string): boolean {
  return /\s/.test(char)
}

function isDigit(char: string): boolean {
  return /[0-9]/.test(char)
}

function isIdentifierStart(char: string): boolean {
  return /[A-Za-z_$]/.test(char)
}

function isIdentifierPart(char: string): boolean {
  return /[A-Za-z0-9_$]/.test(char)
}

function tokenize(source: string): Token[] {
  if (source.length > MAX_FORMULA_LENGTH) {
    throw new Error('Formula is too long')
  }

  const tokens: Token[] = []
  let index = 0

  while (index < source.length) {
    const char = source[index]

    if (isWhitespace(char)) {
      index += 1
      continue
    }

    if (isDigit(char) || (char === '.' && isDigit(source[index + 1] || ''))) {
      const start = index
      index += 1
      while (isDigit(source[index] || '')) index += 1
      if (source[index] === '.') {
        index += 1
        while (isDigit(source[index] || '')) index += 1
      }
      tokens.push({ type: 'number', value: source.slice(start, index) })
      continue
    }

    if (isIdentifierStart(char)) {
      const start = index
      index += 1
      while (isIdentifierPart(source[index] || '')) index += 1
      tokens.push({ type: 'identifier', value: source.slice(start, index) })
      continue
    }

    if (char === '(') {
      tokens.push({ type: 'leftParen', value: char })
      index += 1
      continue
    }

    if (char === ')') {
      tokens.push({ type: 'rightParen', value: char })
      index += 1
      continue
    }

    if (char === '?') {
      tokens.push({ type: 'question', value: char })
      index += 1
      continue
    }

    if (char === ':') {
      tokens.push({ type: 'colon', value: char })
      index += 1
      continue
    }

    const operator = OPERATORS.find(op => source.startsWith(op, index))
    if (!operator) {
      throw new Error(`Unsupported token: ${char}`)
    }
    tokens.push({ type: 'operator', value: operator })
    index += operator.length
  }

  if (tokens.length > MAX_TOKENS) {
    throw new Error('Formula has too many tokens')
  }

  tokens.push({ type: 'eof', value: '' })
  return tokens
}

class SafeFormulaParser {
  private readonly tokens: Token[]
  private readonly params: Record<string, unknown>
  private cursor = 0

  constructor(source: string, params: Record<string, unknown>) {
    this.tokens = tokenize(source)
    this.params = params
  }

  parse(): number | boolean {
    const result = this.parseConditional()
    if (this.current().type !== 'eof') {
      throw new Error('Unexpected trailing token')
    }
    return result
  }

  private current(): Token {
    return this.tokens[this.cursor]
  }

  private consume(value?: string): Token {
    const token = this.current()
    if (value != null && token.value !== value) {
      throw new Error(`Expected ${value}`)
    }
    this.cursor += 1
    return token
  }

  private match(...values: string[]): boolean {
    const token = this.current()
    if (token.type !== 'operator' || !values.includes(token.value)) return false
    this.cursor += 1
    return true
  }

  private parseConditional(): number | boolean {
    const condition = this.parseOr()
    if (this.current().type !== 'question') {
      return condition
    }

    this.consume('?')
    const whenTrue = this.parseConditional()
    if (this.current().type !== 'colon') {
      throw new Error('Expected conditional separator')
    }
    this.consume(':')
    const whenFalse = this.parseConditional()
    return condition ? whenTrue : whenFalse
  }

  private parseOr(): number | boolean {
    let left = this.parseAnd()
    while (this.match('||')) {
      const right = this.parseAnd()
      left = Boolean(left) || Boolean(right)
    }
    return left
  }

  private parseAnd(): number | boolean {
    let left = this.parseComparison()
    while (this.match('&&')) {
      const right = this.parseComparison()
      left = Boolean(left) && Boolean(right)
    }
    return left
  }

  private parseComparison(): number | boolean {
    let left = this.parseAdditive()

    while (this.current().type === 'operator' && ['<', '<=', '>', '>=', '==', '!=', '===', '!=='].includes(this.current().value)) {
      const operator = this.consume().value
      const right = this.parseAdditive()

      switch (operator) {
        case '<':
          left = Number(left) < Number(right)
          break
        case '<=':
          left = Number(left) <= Number(right)
          break
        case '>':
          left = Number(left) > Number(right)
          break
        case '>=':
          left = Number(left) >= Number(right)
          break
        case '==':
        case '===':
          left = left === right
          break
        case '!=':
        case '!==':
          left = left !== right
          break
      }
    }

    return left
  }

  private parseAdditive(): number | boolean {
    let left = this.parseMultiplicative()

    while (this.current().type === 'operator' && ['+', '-'].includes(this.current().value)) {
      const operator = this.consume().value
      const right = this.parseMultiplicative()
      left = operator === '+' ? Number(left) + Number(right) : Number(left) - Number(right)
    }

    return left
  }

  private parseMultiplicative(): number | boolean {
    let left = this.parseUnary()

    while (this.current().type === 'operator' && ['*', '/', '%'].includes(this.current().value)) {
      const operator = this.consume().value
      const right = Number(this.parseUnary())
      if ((operator === '/' || operator === '%') && right === 0) {
        throw new Error('Division by zero')
      }
      if (operator === '*') left = Number(left) * right
      if (operator === '/') left = Number(left) / right
      if (operator === '%') left = Number(left) % right
    }

    return left
  }

  private parseUnary(): number | boolean {
    if (this.match('!')) return !this.parseUnary()
    if (this.match('-')) return -Number(this.parseUnary())
    if (this.match('+')) return Number(this.parseUnary())
    return this.parsePrimary()
  }

  private parsePrimary(): number | boolean {
    const token = this.current()

    if (token.type === 'number') {
      this.consume()
      const value = Number(token.value)
      if (!Number.isFinite(value)) {
        throw new Error('Invalid number')
      }
      return value
    }

    if (token.type === 'identifier') {
      this.consume()
      const value = this.params[token.value]
      if (typeof value === 'number' || typeof value === 'boolean') return value
      if (typeof value === 'string' && value.trim() !== '') {
        const parsed = Number(value)
        if (Number.isFinite(parsed)) return parsed
      }
      throw new Error(`Missing numeric parameter: ${token.value}`)
    }

    if (token.type === 'leftParen') {
      this.consume('(')
      const value = this.parseConditional()
      if (this.current().type !== 'rightParen') {
        throw new Error('Expected closing parenthesis')
      }
      this.consume(')')
      return value
    }

    throw new Error('Expected value')
  }
}

export function evaluateSafeFormula(source: string, params: Record<string, unknown>): number | boolean {
  return new SafeFormulaParser(source, params).parse()
}
