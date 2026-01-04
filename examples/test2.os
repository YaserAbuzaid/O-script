print "O-script Example: Study Tracker";

class StudyDay {
  fun init(subject, goalMinutes) {
    this.subject = subject;
    this.goal = goalMinutes;
    this.minutes = 0;
    this.checkpoint("morning"); // save initial state
  }

  fun add(m) {
    this.minutes = this.minutes + m;
    assert(this.minutes >= 0, "Minutes cannot be negative.");
  }

  fun summary() {
    // Build a readable string using str() to convert numbers.
    return "Subject: " + this.subject +
           " | Studied: " + str(this.minutes) +
           " / Goal: " + str(this.goal);
  }

  fun reachedGoal() {
    return this.minutes >= this.goal;
  }

  fun bug() {
    // Intentional bug: subtract way too much.
    this.minutes = this.minutes - 999;
  }
}

var d = new StudyDay("Math", 90);

d.add(30);
d.add(25);
print d.summary();

d.bug();
print "After bug: " + d.summary();

d.undo();
print "After undo: " + d.summary();

d.redo();
print "After redo: " + d.summary();

d.rollback("morning");
print "After rollback('morning'): " + d.summary();

if (d.reachedGoal()) {
  print "Goal reached!";
} else {
  print "Goal not reached yet.";
}

print "History:";

