# Author: F E R M I ∞ H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense
import json,unittest
from pathlib import Path
from test_contracts import c_run,function,ROOT
class Scheduler(unittest.TestCase):
    def test_bounded_cpu_shares_and_signal_wakeup(self):
        body=r'''
#include <assert.h>
#include <stdio.h>
#include <signal.h>
#define NR_TASKS 4
#define TASK_RUNNING 0
#define TASK_INTERRUPTIBLE 1
struct task_struct { int state,counter,priority; long alarm; unsigned signal,utime,stime; } states[4];
static struct task_struct *task[NR_TASKS]={&states[0],&states[1],&states[2],&states[3]},*current=&states[0];
#define FIRST_TASK task[0]
#define LAST_TASK task[NR_TASKS-1]
static long jiffies;
static unsigned decisions;
#define switch_to(n) do { current=task[n]; decisions++; } while(0)
'''+function('kernel/sched.c','schedule')+function('kernel/sched.c','do_timer')+r'''
int main(void) {
    int i; unsigned counts[4]={0};
    for(i=1;i<4;i++) states[i].priority=i;
    schedule();
    for(i=0;i<600;i++) { counts[current-states]++; jiffies++; do_timer(1); }
    assert(!counts[0]); assert(counts[1]==100 && counts[2]==200 && counts[3]==300);
    states[1].state=TASK_INTERRUPTIBLE;states[1].signal=1U<<(SIGINT-1);
    schedule();assert(states[1].state==TASK_RUNNING);
    states[1].signal=0;states[1].state=TASK_INTERRUPTIBLE;states[1].alarm=jiffies-1;
    schedule();assert(states[1].signal&(1U<<(SIGALRM-1)));assert(states[1].state==TASK_RUNNING);
    printf("{\"layer\":\"host-production-scheduler-stub-switch\",\"ticks\":600,\"shares\":[%u,%u,%u],\"decisions\":%u}\n",counts[1],counts[2],counts[3],decisions);
    return 0;
}
'''
        output=c_run(body,sanitize=True)
        report=json.loads(output)
        self.assertEqual(report['shares'],[100,200,300])
        directory=ROOT/'build/round25';directory.mkdir(parents=True,exist_ok=True)
        (directory/'scheduler.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':unittest.main()
