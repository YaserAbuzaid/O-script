
class A {
  fun init() { this.x = 1; }
  fun set(v) { this.x = v; }
}

var a = new A();
a.set(10);
a.checkpoint("good");
a.set(99);
print a.x; // 99
a.rollback("good");
print a.x; // 10
a.undo(); // undo rollback -> should go back to 99 (snapshot undo)
print a.x; // 99
