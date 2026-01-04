class Counter {
  fun init(v) { this.value = v; }
  fun inc() { this.value = this.value + 1; }
}

var c = new Counter(0);
c.inc();
c.inc();
print c.value; // 2
c.undo();
print c.value; // 1
c.undo();
print c.value; // 0
c.redo();
print c.value; // 1
