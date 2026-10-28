// The open incident: a short, in-world objective chain.
export class Tickets {
  constructor(hud, fault) {
    this.hud = hud;
    this.fault = fault;
    this.t = {
      id: 'INC-48213',
      sev: 'MAJOR',
      title: `PSU redundancy lost on ${fault.hostname}`,
      resolved: false,
      steps: [
        { text: `Find ${fault.hostname} in row B and open its rack door`, done: false },
        { text: 'Check the rear in the hot aisle: is PSU 2 cabled?', done: false },
        { text: 'Read supply air temperature on CRAC-02', done: false },
      ],
    };
    hud.ticket(this.t);
  }

  update(target, player) {
    const step = this.t.steps.findIndex((s) => !s.done);
    if (step < 0) return;
    const f = this.fault;
    let done = false, msg = '';
    if (step === 0 && target?.device === f && f.rack.door > 1.0) {
      done = true;
      msg = `Found it: ${f.rack.id}, U${f.u}. Health LED blinking amber.`;
    } else if (step === 1 && target?.device === f && Math.abs(player.z) < 0.6) {
      done = true;
      msg = 'PSU 2 has no power cord, and its LED is amber. Cable reseated, redundancy restored.';
    } else if (step === 2 && target?.kind === 'crac' && target.name === 'CRAC-02') {
      done = true;
      msg = `Supply air ${target.sup.toFixed(1)} °C. Inside the ASHRAE 18–27 °C envelope.`;
    }
    if (!done) return;
    this.t.steps[step].done = true;
    if (this.t.steps.every((s) => s.done)) {
      this.t.resolved = true;
      msg += ' Ticket closed. The hall is yours.';
    }
    this.hud.ticket(this.t);
    this.hud.toast(msg, 6000);
  }
}
