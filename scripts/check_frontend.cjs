// Pure numerical and syntax checks; browser journeys are recorded separately.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
for (const name of fs.readdirSync(path.join(root, 'static/js'))) {
  if (name.endsWith('.js')) new vm.Script(fs.readFileSync(path.join(root, 'static/js', name), 'utf8'), {filename:name});
}
const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(root,'static/js/analytics.js'),'utf8')+';this.analytics=Analytics;', sandbox);
const a=sandbox.analytics;
const linear=a.computeDerivatives([0,1,2],{X:[0,2,4]}).X;
assert.equal(linear.avgVelocity,2);
assert.equal(linear.maxAcceleration,0);
const partial=a.computeDerivatives([0,1,1.5],{X:[0,2,3]}).X;
assert.equal(partial.avgVelocity,2);
assert.equal(partial.maxAcceleration,0);
assert.equal(a.detectPattern([5,5,5,5]),'constant');
console.log('Frontend scripts parse; derivative and constant-series checks passed.');
