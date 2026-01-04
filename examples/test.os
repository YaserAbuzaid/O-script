// test.os (starter file)
print "Hello from O-script!";

class Person {
  fun init(name) { this.name = name; }
  fun rename(newName) { this.name = newName; }
}

var p = new Person("Ejev");
print p.name;

p.rename("New Name");
print p.name;

// time travel:
p.undo();
print "After undo:";
print p.name;
