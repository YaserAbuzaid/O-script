// O-script "woaaah" demo: time-travel objects + checkpoints
class BankAccount {
  fun init(owner, start) {
    this.owner = owner;
    this.balance = start;
  }

  fun deposit(x) { this.balance = this.balance + x; }
  fun withdraw(x) { this.balance = this.balance - x; }
}

var a = new BankAccount("Ejev", 100);
print a.owner;
print a.balance;

a.deposit(50);
a.withdraw(10);

// save a "good" checkpoint
a.checkpoint("safe");

// mistake
a.withdraw(999); // oops, negative balance (bug / mistake)

print "After mistake:";
print a.balance;

// rollback is ONE undoable action
print "Rollback to safe:";
a.rollback("safe");
print a.balance;

// undo rollback (back to the mistake)
print "Undo rollback (back to mistake):";
a.undo();
print a.balance;

// redo rollback (safe again)
print "Redo rollback (safe again):";
a.redo();
print a.balance;

// inspect history
print "History:";
print a.history();
