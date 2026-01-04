
#!/usr/bin/env python3
"""
O-script — a tiny OOP language with time-travel objects.

Core idea:
- Every object keeps a history of field changes.
- You can call: obj.undo(); obj.redo(); obj.history();
 - You can also create named checkpoints: obj.checkpoint("name"); obj.rollback("name");

Syntax is Lox/JS-ish:
- Statements end with ;
- Blocks use { ... }
- Define classes with methods (methods use 'fun' keyword).
- Construct with: new ClassName(args...)

Example:
class Counter {
  fun init(v) { this.value = v; }
  fun inc() { this.value = this.value + 1; }
}
var c = new Counter(0);
c.inc();
print c.value; // 1
c.undo();
print c.value; // 0
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional, List, Dict, Tuple, Protocol
import enum
import argparse
import json
import time
import sys

# ---------------------------
# Lexer
# ---------------------------

class TokenType(enum.Enum):
    LEFT_PAREN="("
    RIGHT_PAREN=")"
    LEFT_BRACE="{"
    RIGHT_BRACE="}"
    COMMA=","
    DOT="."
    MINUS="-"
    PLUS="+"
    SEMICOLON=";"
    SLASH="/"
    STAR="*"

    BANG="!"
    BANG_EQUAL="!="
    EQUAL="="
    EQUAL_EQUAL="=="
    GREATER=">"
    GREATER_EQUAL=">="
    LESS="<"
    LESS_EQUAL="<="

    IDENTIFIER="IDENT"
    STRING="STRING"
    NUMBER="NUMBER"

    AND="and"
    CLASS="class"
    ELSE="else"
    FALSE="false"
    FUN="fun"
    IF="if"
    NIL="nil"
    OR="or"
    PRINT="print"
    RETURN="return"
    THIS="this"
    TRUE="true"
    VAR="var"
    WHILE="while"
    NEW="new"

    EOF="EOF"

KEYWORDS = {t.value:t for t in [
    TokenType.AND, TokenType.CLASS, TokenType.ELSE, TokenType.FALSE, TokenType.FUN,
    TokenType.IF, TokenType.NIL, TokenType.OR, TokenType.PRINT, TokenType.RETURN,
    TokenType.THIS, TokenType.TRUE, TokenType.VAR, TokenType.WHILE, TokenType.NEW
]}

@dataclass
class Token:
    type: TokenType
    lexeme: str
    literal: Any
    line: int

class ScanError(Exception):
    pass

class Scanner:
    def __init__(self, source:str):
        self.source=source
        self.tokens: List[Token]=[]
        self.start=0
        self.current=0
        self.line=1

    def scan_tokens(self)->List[Token]:
        while not self.is_at_end():
            self.start=self.current
            self.scan_token()
        self.tokens.append(Token(TokenType.EOF,"",None,self.line))
        return self.tokens

    def is_at_end(self)->bool:
        return self.current>=len(self.source)

    def advance(self)->str:
        ch=self.source[self.current]
        self.current+=1
        return ch

    def add_token(self, type_:TokenType, literal:Any=None):
        text=self.source[self.start:self.current]
        self.tokens.append(Token(type_, text, literal, self.line))

    def match(self, expected:str)->bool:
        if self.is_at_end(): return False
        if self.source[self.current]!=expected: return False
        self.current+=1
        return True

    def peek(self)->str:
        if self.is_at_end(): return "\0"
        return self.source[self.current]

    def peek_next(self)->str:
        if self.current+1>=len(self.source): return "\0"
        return self.source[self.current+1]

    def scan_token(self):
        c=self.advance()
        if c=="(":
            self.add_token(TokenType.LEFT_PAREN)
        elif c==")":
            self.add_token(TokenType.RIGHT_PAREN)
        elif c=="{":
            self.add_token(TokenType.LEFT_BRACE)
        elif c=="}":
            self.add_token(TokenType.RIGHT_BRACE)
        elif c==",":
            self.add_token(TokenType.COMMA)
        elif c==".":
            self.add_token(TokenType.DOT)
        elif c=="-":
            self.add_token(TokenType.MINUS)
        elif c=="+":
            self.add_token(TokenType.PLUS)
        elif c==";":
            self.add_token(TokenType.SEMICOLON)
        elif c=="*":
            self.add_token(TokenType.STAR)
        elif c=="!":
            self.add_token(TokenType.BANG_EQUAL if self.match("=") else TokenType.BANG)
        elif c=="=":
            self.add_token(TokenType.EQUAL_EQUAL if self.match("=") else TokenType.EQUAL)
        elif c=="<":
            self.add_token(TokenType.LESS_EQUAL if self.match("=") else TokenType.LESS)
        elif c==">":
            self.add_token(TokenType.GREATER_EQUAL if self.match("=") else TokenType.GREATER)
        elif c=="/":
            if self.match("/"):
                while self.peek()!="\n" and not self.is_at_end():
                    self.advance()
            else:
                self.add_token(TokenType.SLASH)
        elif c in (" ", "\r", "\t"):
            return
        elif c=="\n":
            self.line+=1
        elif c=="\"":
            self.string()
        else:
            if c.isdigit():
                self.number()
            elif c.isalpha() or c=="_":
                self.identifier()
            else:
                raise ScanError(f"[line {self.line}] Unexpected character: {c!r}")

    def string(self):
        while self.peek()!="\"" and not self.is_at_end():
            if self.peek()=="\n":
                self.line+=1
            self.advance()
        if self.is_at_end():
            raise ScanError(f"[line {self.line}] Unterminated string.")
        self.advance() # closing "
        value=self.source[self.start+1:self.current-1]
        self.add_token(TokenType.STRING, value)

    def number(self):
        while self.peek().isdigit():
            self.advance()
        if self.peek()=="." and self.peek_next().isdigit():
            self.advance()
            while self.peek().isdigit():
                self.advance()
        value=float(self.source[self.start:self.current])
        self.add_token(TokenType.NUMBER, value)

    def identifier(self):
        while self.peek().isalnum() or self.peek()=="_":
            self.advance()
        text=self.source[self.start:self.current]
        type_=KEYWORDS.get(text, TokenType.IDENTIFIER)
        self.add_token(type_)

# ---------------------------
# AST
# ---------------------------

class Expr: pass
class Stmt: pass

@dataclass
class Literal(Expr):
    value: Any

@dataclass
class Grouping(Expr):
    expression: Expr

@dataclass
class Unary(Expr):
    operator: Token
    right: Expr

@dataclass
class Binary(Expr):
    left: Expr
    operator: Token
    right: Expr

@dataclass
class Variable(Expr):
    name: Token

@dataclass
class Assign(Expr):
    name: Token
    value: Expr

@dataclass
class Logical(Expr):
    left: Expr
    operator: Token
    right: Expr

@dataclass
class Call(Expr):
    callee: Expr
    paren: Token
    arguments: List[Expr]

@dataclass
class Get(Expr):
    object: Expr
    name: Token

@dataclass
class SetExpr(Expr):
    object: Expr
    name: Token
    value: Expr

@dataclass
class This(Expr):
    keyword: Token

@dataclass
class NewExpr(Expr):
    class_name: Token
    arguments: List[Expr]

@dataclass
class ExpressionStmt(Stmt):
    expression: Expr

@dataclass
class PrintStmt(Stmt):
    expression: Expr

@dataclass
class VarStmt(Stmt):
    name: Token
    initializer: Optional[Expr]

@dataclass
class BlockStmt(Stmt):
    statements: List[Stmt]

@dataclass
class IfStmt(Stmt):
    condition: Expr
    then_branch: Stmt
    else_branch: Optional[Stmt]

@dataclass
class WhileStmt(Stmt):
    condition: Expr
    body: Stmt

@dataclass
class FunctionStmt(Stmt):
    name: Token
    params: List[Token]
    body: List[Stmt]

@dataclass
class ReturnStmt(Stmt):
    keyword: Token
    value: Optional[Expr]

@dataclass
class ClassStmt(Stmt):
    name: Token
    methods: List[FunctionStmt]

# ---------------------------
# Parser
# ---------------------------

class ParseError(Exception):
    pass

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens=tokens
        self.current=0

    def parse(self)->List[Stmt]:
        statements=[]
        while not self.is_at_end():
            statements.append(self.declaration())
        return statements

    def declaration(self)->Stmt:
        if self.match(TokenType.CLASS):
            return self.class_declaration()
        if self.match(TokenType.FUN):
            return self.function("function")
        if self.match(TokenType.VAR):
            return self.var_declaration()
        return self.statement()

    def class_declaration(self)->Stmt:
        name=self.consume(TokenType.IDENTIFIER, "Expect class name.")
        self.consume(TokenType.LEFT_BRACE, "Expect '{' before class body.")
        methods=[]
        while not self.check(TokenType.RIGHT_BRACE) and not self.is_at_end():
            self.consume(TokenType.FUN, "Expect 'fun' before method declaration.")
            methods.append(self.function("method"))
        self.consume(TokenType.RIGHT_BRACE, "Expect '}' after class body.")
        return ClassStmt(name, methods)

    def function(self, kind:str)->FunctionStmt:
        name=self.consume(TokenType.IDENTIFIER, f"Expect {kind} name.")
        self.consume(TokenType.LEFT_PAREN, f"Expect '(' after {kind} name.")
        params=[]
        if not self.check(TokenType.RIGHT_PAREN):
            while True:
                if len(params)>=255:
                    raise self.error(self.peek(), "Can't have more than 255 parameters.")
                params.append(self.consume(TokenType.IDENTIFIER, "Expect parameter name."))
                if not self.match(TokenType.COMMA):
                    break
        self.consume(TokenType.RIGHT_PAREN, "Expect ')' after parameters.")
        self.consume(TokenType.LEFT_BRACE, f"Expect '{{' before {kind} body.")
        body=self.block()
        return FunctionStmt(name, params, body)

    def var_declaration(self)->VarStmt:
        name=self.consume(TokenType.IDENTIFIER, "Expect variable name.")
        initializer=None
        if self.match(TokenType.EQUAL):
            initializer=self.expression()
        self.consume(TokenType.SEMICOLON, "Expect ';' after variable declaration.")
        return VarStmt(name, initializer)

    def statement(self)->Stmt:
        if self.match(TokenType.PRINT):
            return self.print_statement()
        if self.match(TokenType.LEFT_BRACE):
            return BlockStmt(self.block())
        if self.match(TokenType.IF):
            return self.if_statement()
        if self.match(TokenType.WHILE):
            return self.while_statement()
        if self.match(TokenType.RETURN):
            return self.return_statement()
        return self.expression_statement()

    def return_statement(self)->Stmt:
        keyword=self.previous()
        value=None
        if not self.check(TokenType.SEMICOLON):
            value=self.expression()
        self.consume(TokenType.SEMICOLON, "Expect ';' after return value.")
        return ReturnStmt(keyword, value)

    def if_statement(self)->Stmt:
        self.consume(TokenType.LEFT_PAREN, "Expect '(' after 'if'.")
        condition=self.expression()
        self.consume(TokenType.RIGHT_PAREN, "Expect ')' after if condition.")
        then_branch=self.statement()
        else_branch=None
        if self.match(TokenType.ELSE):
            else_branch=self.statement()
        return IfStmt(condition, then_branch, else_branch)

    def while_statement(self)->Stmt:
        self.consume(TokenType.LEFT_PAREN, "Expect '(' after 'while'.")
        condition=self.expression()
        self.consume(TokenType.RIGHT_PAREN, "Expect ')' after condition.")
        body=self.statement()
        return WhileStmt(condition, body)

    def block(self)->List[Stmt]:
        statements=[]
        while not self.check(TokenType.RIGHT_BRACE) and not self.is_at_end():
            statements.append(self.declaration())
        self.consume(TokenType.RIGHT_BRACE, "Expect '}' after block.")
        return statements

    def print_statement(self)->Stmt:
        value=self.expression()
        self.consume(TokenType.SEMICOLON, "Expect ';' after value.")
        return PrintStmt(value)

    def expression_statement(self)->Stmt:
        expr=self.expression()
        self.consume(TokenType.SEMICOLON, "Expect ';' after expression.")
        return ExpressionStmt(expr)

    def expression(self)->Expr:
        return self.assignment()

    def assignment(self)->Expr:
        expr=self.or_()
        if self.match(TokenType.EQUAL):
            equals=self.previous()
            value=self.assignment()
            if isinstance(expr, Variable):
                return Assign(expr.name, value)
            if isinstance(expr, Get):
                return SetExpr(expr.object, expr.name, value)
            raise self.error(equals, "Invalid assignment target.")
        return expr

    def or_(self)->Expr:
        expr=self.and_()
        while self.match(TokenType.OR):
            op=self.previous()
            right=self.and_()
            expr=Logical(expr, op, right)
        return expr

    def and_(self)->Expr:
        expr=self.equality()
        while self.match(TokenType.AND):
            op=self.previous()
            right=self.equality()
            expr=Logical(expr, op, right)
        return expr

    def equality(self)->Expr:
        expr=self.comparison()
        while self.match(TokenType.BANG_EQUAL, TokenType.EQUAL_EQUAL):
            op=self.previous()
            right=self.comparison()
            expr=Binary(expr, op, right)
        return expr

    def comparison(self)->Expr:
        expr=self.term()
        while self.match(TokenType.GREATER, TokenType.GREATER_EQUAL, TokenType.LESS, TokenType.LESS_EQUAL):
            op=self.previous()
            right=self.term()
            expr=Binary(expr, op, right)
        return expr

    def term(self)->Expr:
        expr=self.factor()
        while self.match(TokenType.MINUS, TokenType.PLUS):
            op=self.previous()
            right=self.factor()
            expr=Binary(expr, op, right)
        return expr

    def factor(self)->Expr:
        expr=self.unary()
        while self.match(TokenType.SLASH, TokenType.STAR):
            op=self.previous()
            right=self.unary()
            expr=Binary(expr, op, right)
        return expr

    def unary(self)->Expr:
        if self.match(TokenType.BANG, TokenType.MINUS):
            op=self.previous()
            right=self.unary()
            return Unary(op, right)
        return self.call()

    def call(self)->Expr:
        expr=self.primary()
        while True:
            if self.match(TokenType.LEFT_PAREN):
                expr=self.finish_call(expr)
            elif self.match(TokenType.DOT):
                name=self.consume(TokenType.IDENTIFIER, "Expect property name after '.'.")
                expr=Get(expr, name)
            else:
                break
        return expr

    def finish_call(self, callee:Expr)->Expr:
        args=[]
        if not self.check(TokenType.RIGHT_PAREN):
            while True:
                if len(args)>=255:
                    raise self.error(self.peek(), "Can't have more than 255 arguments.")
                args.append(self.expression())
                if not self.match(TokenType.COMMA):
                    break
        paren=self.consume(TokenType.RIGHT_PAREN, "Expect ')' after arguments.")
        return Call(callee, paren, args)

    def primary(self)->Expr:
        if self.match(TokenType.FALSE):
            return Literal(False)
        if self.match(TokenType.TRUE):
            return Literal(True)
        if self.match(TokenType.NIL):
            return Literal(None)
        if self.match(TokenType.NUMBER, TokenType.STRING):
            return Literal(self.previous().literal)
        if self.match(TokenType.THIS):
            return This(self.previous())
        if self.match(TokenType.NEW):
            class_name=self.consume(TokenType.IDENTIFIER, "Expect class name after 'new'.")
            self.consume(TokenType.LEFT_PAREN, "Expect '(' after class name.")
            args=[]
            if not self.check(TokenType.RIGHT_PAREN):
                while True:
                    args.append(self.expression())
                    if not self.match(TokenType.COMMA):
                        break
            self.consume(TokenType.RIGHT_PAREN, "Expect ')' after arguments.")
            return NewExpr(class_name, args)
        if self.match(TokenType.IDENTIFIER):
            return Variable(self.previous())
        if self.match(TokenType.LEFT_PAREN):
            expr=self.expression()
            self.consume(TokenType.RIGHT_PAREN, "Expect ')' after expression.")
            return Grouping(expr)
        raise self.error(self.peek(), "Expect expression.")

    # helpers
    def match(self, *types:TokenType)->bool:
        for t in types:
            if self.check(t):
                self.advance()
                return True
        return False

    def consume(self, type_:TokenType, message:str)->Token:
        if self.check(type_):
            return self.advance()
        raise self.error(self.peek(), message)

    def check(self, type_:TokenType)->bool:
        if self.is_at_end(): return False
        return self.peek().type==type_

    def advance(self)->Token:
        if not self.is_at_end():
            self.current+=1
        return self.previous()

    def is_at_end(self)->bool:
        return self.peek().type==TokenType.EOF

    def peek(self)->Token:
        return self.tokens[self.current]

    def previous(self)->Token:
        return self.tokens[self.current-1]

    def error(self, token:Token, message:str)->ParseError:
        return ParseError(f"[line {token.line}] Error at '{token.lexeme}': {message}")

# ---------------------------
# Runtime
# ---------------------------

class RuntimeError_(Exception):
    def __init__(self, token:Token, message:str):
        super().__init__(message)
        self.token=token
        self.message=message
    def __str__(self):
        return f"[line {self.token.line}] RuntimeError: {self.message}"

class ReturnException(Exception):
    def __init__(self, value:Any):
        self.value=value

class Environment:
    def __init__(self, enclosing:'Environment'=None):
        self.enclosing=enclosing
        self.values: Dict[str, Any] = {}
    def define(self, name:str, value:Any):
        self.values[name]=value
    def get(self, name_token:Token)->Any:
        name=name_token.lexeme
        if name in self.values:
            return self.values[name]
        if self.enclosing:
            return self.enclosing.get(name_token)
        raise RuntimeError_(name_token, f"Undefined variable '{name}'.")
    def assign(self, name_token:Token, value:Any):
        name=name_token.lexeme
        if name in self.values:
            self.values[name]=value
            return
        if self.enclosing:
            self.enclosing.assign(name_token, value)
            return
        raise RuntimeError_(name_token, f"Undefined variable '{name}'.")

class OCallable(Protocol):
    def arity(self)->int: ...
    def call(self, interpreter:'Interpreter', arguments:List[Any])->Any: ...

class NativeFunction:
    def __init__(self, name:str, arity_:int, func):
        self._name=name
        self._arity=arity_
        self._func=func
    def arity(self)->int:
        return self._arity
    def call(self, interpreter:'Interpreter', arguments:List[Any])->Any:
        return self._func(interpreter, *arguments)
    def __str__(self)->str:
        return f"<native fn {self._name}>"

class OFunction:
    def __init__(self, declaration:FunctionStmt, closure:Environment, is_initializer:bool=False):
        self.declaration=declaration
        self.closure=closure
        self.is_initializer=is_initializer
    def bind(self, instance:'OInstance')->'OFunction':
        env=Environment(self.closure)
        env.define("this", instance)
        return OFunction(self.declaration, env, self.is_initializer)
    def arity(self)->int:
        return len(self.declaration.params)
    def call(self, interpreter:'Interpreter', arguments:List[Any])->Any:
        env=Environment(self.closure)
        for param, arg in zip(self.declaration.params, arguments):
            env.define(param.lexeme, arg)
        try:
            interpreter.execute_block(self.declaration.body, env)
        except ReturnException as r:
            if self.is_initializer:
                return self.closure.values.get("this")
            return r.value
        if self.is_initializer:
            return self.closure.values.get("this")
        return None
    def __str__(self)->str:
        return f"<fn {self.declaration.name.lexeme}>"

class OClass:
    def __init__(self, name:str, methods:Dict[str, OFunction]):
        self.name=name
        self.methods=methods
    def find_method(self, name:str)->Optional[OFunction]:
        return self.methods.get(name)
    def arity(self)->int:
        initializer=self.find_method("init")
        if initializer:
            return initializer.arity()
        return 0
    def call(self, interpreter:'Interpreter', arguments:List[Any])->Any:
        instance=interpreter.make_instance(self)
        initializer=self.find_method("init")
        if initializer:
            initializer.bind(instance).call(interpreter, arguments)
        return instance
    def __str__(self)->str:
        return f"<class {self.name}>"

_UNDEFINED = object()

class OInstance:
    def __init__(self, klass:OClass, obj_id:int):
        self.klass=klass
        self.id=obj_id
        self.fields: Dict[str, Any] = {}
        # patches: (field, old, new, step, line)
        self.past: List[Tuple[str, Any, Any, int, int]]=[]
        self.future: List[Tuple[str, Any, Any, int, int]]=[]
        # named snapshots: name -> {field: value}
        self.checkpoints: Dict[str, Dict[str, Any]] = {}

    def get(self, name_token:Token, interpreter:'Interpreter')->Any:
        name=name_token.lexeme
        if name in self.fields:
            return self.fields[name]
        method=self.klass.find_method(name)
        if method:
            return method.bind(self)

        # Built-in time travel methods:
        if name=="undo":
            return NativeFunction(f"{self.klass.name}.undo", 0, lambda interp: self._undo(interp, name_token.line))
        if name=="redo":
            return NativeFunction(f"{self.klass.name}.redo", 0, lambda interp: self._redo(interp, name_token.line))
        if name=="history":
            return NativeFunction(f"{self.klass.name}.history", 0, lambda interp: self._history(interp))
        if name=="id":
            return NativeFunction(f"{self.klass.name}.id", 0, lambda interp: self.id)

        # Named snapshots (extra time travel):
        # - obj.checkpoint("name");
        # - obj.rollback("name");
        # - obj.checkpoints();
        if name=="checkpoint":
            return NativeFunction(f"{self.klass.name}.checkpoint", 1, lambda interp, label: self._checkpoint(interp, label, name_token.line))
        if name=="rollback":
            return NativeFunction(f"{self.klass.name}.rollback", 1, lambda interp, label: self._rollback(interp, label, name_token.line))
        if name=="checkpoints":
            return NativeFunction(f"{self.klass.name}.checkpoints", 0, lambda interp: list(self.checkpoints.keys()))

        raise RuntimeError_(name_token, f"Undefined property '{name}'.")

    def set(self, name_token:Token, value:Any, interpreter:'Interpreter'):
        field=name_token.lexeme
        old=self.fields.get(field, _UNDEFINED)
        step=interpreter.next_step()
        self.past.append((field, old, value, step, name_token.line))
        self.future.clear()
        self.fields[field]=value
        interpreter.record_event({
            "type":"set",
            "step":step,
            "line":name_token.line,
            "object": self._obj_label(),
            "field": field,
            "old": interpreter.serialize_value(old),
            "new": interpreter.serialize_value(value),
            "fields_after": self._serialize_fields(interpreter)
        })

    def _undo(self, interpreter:'Interpreter', line:int):
        if not self.past:
            return None
        field, old, new, orig_step, orig_line = self.past.pop()
        step=interpreter.next_step()

        # Special case: snapshot patch (used by rollback)
        if field=="__snapshot__":
            # old/new are dict snapshots of fields
            self.fields = dict(old)
        else:
            if old is _UNDEFINED:
                if field in self.fields:
                    del self.fields[field]
            else:
                self.fields[field]=old

        self.future.append((field, old, new, orig_step, orig_line))
        interpreter.record_event({
            "type":"undo",
            "step":step,
            "line":line,
            "object": self._obj_label(),
            "field": field,
            "old": interpreter.serialize_value(new),
            "new": interpreter.serialize_value(old),
            "fields_after": self._serialize_fields(interpreter),
            "rewinds_step": orig_step
        })
        return None

    def _redo(self, interpreter:'Interpreter', line:int):
        if not self.future:
            return None
        field, old, new, orig_step, orig_line = self.future.pop()
        step=interpreter.next_step()

        # Special case: snapshot patch (used by rollback)
        if field=="__snapshot__":
            self.fields = dict(new)
        else:
            self.fields[field]=new
        self.past.append((field, old, new, orig_step, orig_line))
        interpreter.record_event({
            "type":"redo",
            "step":step,
            "line":line,
            "object": self._obj_label(),
            "field": field,
            "old": interpreter.serialize_value(old),
            "new": interpreter.serialize_value(new),
            "fields_after": self._serialize_fields(interpreter),
            "reapplies_step": orig_step
        })
        return None

    def _history(self, interpreter:'Interpreter'):
        hist=[]
        for field, old, new, step, line in self.past:
            hist.append({
                "step": step,
                "line": line,
                "field": field,
                "old": interpreter.serialize_value(old),
                "new": interpreter.serialize_value(new),
            })
        return hist

    def _checkpoint(self, interpreter:'Interpreter', label:Any, line:int):
        # Checkpoints store a named snapshot of this object's fields.
        name = label if isinstance(label, str) else interpreter.serialize_value(label)
        self.checkpoints[name] = dict(self.fields)
        step = interpreter.next_step()
        interpreter.record_event({
            "type":"checkpoint",
            "step": step,
            "line": line,
            "object": self._obj_label(),
            "name": name,
            "fields_after": self._serialize_fields(interpreter)
        })
        return None

    def _rollback(self, interpreter:'Interpreter', label:Any, line:int):
        # Roll back this object's fields to a named checkpoint.
        name = label if isinstance(label, str) else interpreter.serialize_value(label)
        if name not in self.checkpoints:
            raise RuntimeError_(Token(TokenType.IDENTIFIER, "rollback", None, line), f"No checkpoint named '{name}'.")
        old_snapshot = dict(self.fields)
        new_snapshot = dict(self.checkpoints[name])

        step = interpreter.next_step()
        # Atomic snapshot patch so undo/redo treats rollback as ONE action.
        self.past.append(("__snapshot__", old_snapshot, new_snapshot, step, line))
        self.future.clear()
        self.fields = dict(new_snapshot)

        interpreter.record_event({
            "type":"rollback",
            "step": step,
            "line": line,
            "object": self._obj_label(),
            "name": name,
            "fields_after": self._serialize_fields(interpreter)
        })
        return None

    def _obj_label(self)->str:
        return f"{self.klass.name}#{self.id}"

    def _serialize_fields(self, interpreter:'Interpreter')->Dict[str,str]:
        return {k: interpreter.serialize_value(v) for k,v in self.fields.items()}

    def __str__(self):
        return f"<{self.klass.name}#{self.id}>"

class Interpreter:
    def __init__(self):
        self.globals=Environment()
        self.environment=self.globals
        self._step=0
        self.trace: List[Dict[str,Any]]=[]
        self._next_obj_id=1

        # Built-ins
        self.globals.define("clock", NativeFunction("clock", 0, lambda interp: time.time()))
        self.globals.define("str", NativeFunction("str", 1, lambda interp, v: interp.serialize_value(v)))
        self.globals.define("type", NativeFunction("type", 1, lambda interp, v: interp.type_of(v)))
        self.globals.define("len", NativeFunction("len", 1, lambda interp, v: interp.native_len(v)))
        self.globals.define("input", NativeFunction("input", -1, lambda interp, *args: interp.native_input(*args)))
        self.globals.define("assert", NativeFunction("assert", -1, lambda interp, *args: interp.native_assert(*args)))

    def next_step(self)->int:
        self._step+=1
        return self._step

    def record_event(self, event:Dict[str,Any]):
        self.trace.append(event)

    def make_instance(self, klass:OClass)->OInstance:
        obj=OInstance(klass, self._next_obj_id)
        self._next_obj_id+=1
        step=self.next_step()
        self.record_event({
            "type":"new",
            "step":step,
            "line": None,
            "object": f"{klass.name}#{obj.id}",
            "fields_after": {}
        })
        return obj

    def type_of(self, v:Any)->str:
        if v is None: return "nil"
        if isinstance(v,bool): return "bool"
        if isinstance(v,(int,float)): return "number"
        if isinstance(v,str): return "string"
        if isinstance(v,OInstance): return f"instance({v.klass.name})"
        if isinstance(v,OClass): return f"class({v.name})"
        if isinstance(v,OFunction): return "function"
        if isinstance(v,NativeFunction): return "native_function"
        return type(v).__name__


    def native_len(self, v:Any)->int:
        if isinstance(v, str):
            return len(v)
        if isinstance(v, (list, dict)):
            return len(v)
        raise RuntimeError_(Token(TokenType.IDENTIFIER, "len", None, 0), "len(x) only works on strings, lists, and dicts.")

    def native_input(self, *args:Any)->str:
        # input() or input(prompt)
        if len(args)==0:
            prompt=""
        elif len(args)==1:
            prompt=str(args[0])
        else:
            raise RuntimeError_(Token(TokenType.IDENTIFIER, "input", None, 0), "input() takes 0 or 1 argument.")
        return input(prompt)

    def native_assert(self, *args:Any)->Any:
        # assert(condition) or assert(condition, message)
        if len(args)==0 or len(args)>2:
            raise RuntimeError_(Token(TokenType.IDENTIFIER, "assert", None, 0), "assert(condition[, message]) takes 1 or 2 arguments.")
        cond=args[0]
        msg="Assertion failed."
        if len(args)==2:
            msg=str(args[1])
        if not self.is_truthy(cond):
            raise RuntimeError_(Token(TokenType.IDENTIFIER, "assert", None, 0), msg)
        return None
    def serialize_value(self, v:Any)->str:
        if v is _UNDEFINED:
            return "<undefined>"
        if v is None: return "nil"
        if isinstance(v,bool): return "true" if v else "false"
        if isinstance(v,(int,float)):
            if isinstance(v,float) and v.is_integer():
                return str(int(v))
            return str(v)
        if isinstance(v,str): return v
        if isinstance(v,OInstance): return f"<{v.klass.name}#{v.id}>"
        if isinstance(v,OClass): return f"<class {v.name}>"
        if isinstance(v,(OFunction,NativeFunction)): return str(v)
        if isinstance(v,(list,dict)):
            return json.dumps(v, indent=None, separators=(",",":"))
        return str(v)

    def interpret(self, statements:List[Stmt]):
        for stmt in statements:
            self.execute(stmt)

    def execute(self, stmt:Stmt):
        if isinstance(stmt, ExpressionStmt):
            self.evaluate(stmt.expression)
        elif isinstance(stmt, PrintStmt):
            value=self.evaluate(stmt.expression)
            print(self.serialize_value(value))
        elif isinstance(stmt, VarStmt):
            value=None
            if stmt.initializer:
                value=self.evaluate(stmt.initializer)
            self.environment.define(stmt.name.lexeme, value)
        elif isinstance(stmt, BlockStmt):
            self.execute_block(stmt.statements, Environment(self.environment))
        elif isinstance(stmt, IfStmt):
            if self.is_truthy(self.evaluate(stmt.condition)):
                self.execute(stmt.then_branch)
            elif stmt.else_branch:
                self.execute(stmt.else_branch)
        elif isinstance(stmt, WhileStmt):
            while self.is_truthy(self.evaluate(stmt.condition)):
                self.execute(stmt.body)
        elif isinstance(stmt, FunctionStmt):
            func=OFunction(stmt, self.environment, is_initializer=False)
            self.environment.define(stmt.name.lexeme, func)
        elif isinstance(stmt, ReturnStmt):
            value=None
            if stmt.value:
                value=self.evaluate(stmt.value)
            raise ReturnException(value)
        elif isinstance(stmt, ClassStmt):
            self.environment.define(stmt.name.lexeme, None)
            methods={}
            for method in stmt.methods:
                is_init = (method.name.lexeme=="init")
                methods[method.name.lexeme]=OFunction(method, self.environment, is_initializer=is_init)
            klass=OClass(stmt.name.lexeme, methods)
            self.environment.assign(stmt.name, klass)
        else:
            raise Exception(f"Unknown statement type: {stmt}")

    def execute_block(self, statements:List[Stmt], env:Environment):
        previous=self.environment
        try:
            self.environment=env
            for stmt in statements:
                self.execute(stmt)
        finally:
            self.environment=previous

    def evaluate(self, expr:Expr)->Any:
        if isinstance(expr, Literal):
            return expr.value
        if isinstance(expr, Grouping):
            return self.evaluate(expr.expression)
        if isinstance(expr, Unary):
            right=self.evaluate(expr.right)
            if expr.operator.type==TokenType.MINUS:
                self.check_number_operand(expr.operator, right)
                return -right
            if expr.operator.type==TokenType.BANG:
                return not self.is_truthy(right)
        if isinstance(expr, Binary):
            left=self.evaluate(expr.left)
            right=self.evaluate(expr.right)
            t=expr.operator.type
            if t==TokenType.PLUS:
                if isinstance(left,(int,float)) and isinstance(right,(int,float)):
                    return left+right
                if isinstance(left,str) and isinstance(right,str):
                    return left+right
                raise RuntimeError_(expr.operator, "Operands must be two numbers or two strings.")
            if t==TokenType.MINUS:
                self.check_number_operands(expr.operator,left,right)
                return left-right
            if t==TokenType.STAR:
                self.check_number_operands(expr.operator,left,right)
                return left*right
            if t==TokenType.SLASH:
                self.check_number_operands(expr.operator,left,right)
                if right==0:
                    raise RuntimeError_(expr.operator, "Division by zero.")
                return left/right
            if t==TokenType.GREATER:
                self.check_number_operands(expr.operator,left,right)
                return left>right
            if t==TokenType.GREATER_EQUAL:
                self.check_number_operands(expr.operator,left,right)
                return left>=right
            if t==TokenType.LESS:
                self.check_number_operands(expr.operator,left,right)
                return left<right
            if t==TokenType.LESS_EQUAL:
                self.check_number_operands(expr.operator,left,right)
                return left<=right
            if t==TokenType.EQUAL_EQUAL:
                return self.is_equal(left,right)
            if t==TokenType.BANG_EQUAL:
                return not self.is_equal(left,right)
        if isinstance(expr, Variable):
            return self.environment.get(expr.name)
        if isinstance(expr, Assign):
            value=self.evaluate(expr.value)
            self.environment.assign(expr.name, value)
            return value
        if isinstance(expr, Logical):
            left=self.evaluate(expr.left)
            if expr.operator.type==TokenType.OR:
                if self.is_truthy(left):
                    return left
            else:
                if not self.is_truthy(left):
                    return left
            return self.evaluate(expr.right)
        if isinstance(expr, Call):
            callee=self.evaluate(expr.callee)
            args=[self.evaluate(a) for a in expr.arguments]
            if not hasattr(callee, "call"):
                raise RuntimeError_(expr.paren, "Can only call functions and classes.")
            ar=getattr(callee, "arity", lambda: -1)()
            if ar!=-1 and len(args)!=ar:
                raise RuntimeError_(expr.paren, f"Expected {ar} arguments but got {len(args)}.")
            return callee.call(self, args)
        if isinstance(expr, Get):
            obj=self.evaluate(expr.object)
            if isinstance(obj, OInstance):
                return obj.get(expr.name, self)
            raise RuntimeError_(expr.name, "Only instances have properties.")
        if isinstance(expr, SetExpr):
            obj=self.evaluate(expr.object)
            if not isinstance(obj, OInstance):
                raise RuntimeError_(expr.name, "Only instances have fields.")
            value=self.evaluate(expr.value)
            obj.set(expr.name, value, self)
            return value
        if isinstance(expr, This):
            return self.environment.get(expr.keyword)
        if isinstance(expr, NewExpr):
            klass=self.environment.get(expr.class_name)
            if not isinstance(klass, OClass):
                raise RuntimeError_(expr.class_name, f"'{expr.class_name.lexeme}' is not a class.")
            args=[self.evaluate(a) for a in expr.arguments]
            ar=klass.arity()
            if len(args)!=ar:
                raise RuntimeError_(expr.class_name, f"Expected {ar} arguments but got {len(args)}.")
            return klass.call(self, args)
        raise Exception(f"Unknown expression type: {expr}")

    def is_truthy(self, v:Any)->bool:
        if v is None: return False
        if isinstance(v,bool): return v
        return True

    def is_equal(self,a:Any,b:Any)->bool:
        return a==b

    def check_number_operand(self, operator:Token, operand:Any):
        if isinstance(operand,(int,float)): return
        raise RuntimeError_(operator, "Operand must be a number.")

    def check_number_operands(self, operator:Token, left:Any, right:Any):
        if isinstance(left,(int,float)) and isinstance(right,(int,float)): return
        raise RuntimeError_(operator, "Operands must be numbers.")

# ---------------------------
# Runner / CLI
# ---------------------------

def run_source(source:str, trace_path:Optional[str]=None):
    scanner=Scanner(source)
    tokens=scanner.scan_tokens()
    parser=Parser(tokens)
    stmts=parser.parse()

    interpreter=Interpreter()
    interpreter.interpret(stmts)

    if trace_path:
        with open(trace_path, "w", encoding="utf-8") as f:
            json.dump(interpreter.trace, f, indent=2)
    return 0

def run_file(path:str, trace_path:Optional[str]=None):
    with open(path, "r", encoding="utf-8") as f:
        source=f.read()
    return run_source(source, trace_path=trace_path)

def repl():
    print("O-script REPL. End each statement with ';'. Ctrl+C to exit.")
    interpreter=Interpreter()
    while True:
        try:
            line=input("o> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not line.strip():
            continue
        try:
            scanner=Scanner(line+"\n")
            tokens=scanner.scan_tokens()
            parser=Parser(tokens)
            stmts=parser.parse()
            interpreter.interpret(stmts)
        except Exception as e:
            print(e, file=sys.stderr)

def main(argv:Optional[List[str]]=None):
    p=argparse.ArgumentParser(prog="oscript", description="Run O-script programs.")
    p.add_argument("file", nargs="?", help="Path to .os file to run.")
    p.add_argument("--trace", dest="trace", help="Write execution trace JSON to this file.")
    p.add_argument("--repl", action="store_true", help="Start a REPL.")
    args=p.parse_args(argv)

    try:
        if args.repl or not args.file:
            repl()
            return 0
        return run_file(args.file, trace_path=args.trace)
    except (ScanError, ParseError, RuntimeError_) as e:
        print(e, file=sys.stderr)
        return 65
    except Exception as e:
        print("Internal error:", e, file=sys.stderr)
        return 70

if __name__ == "__main__":
    raise SystemExit(main())