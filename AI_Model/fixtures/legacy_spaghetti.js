/**
 * Legacy Spaghetti Engine - Complex Anomaly Candidate
 */
export function processLegacyPayroll(employee, taxRate, deductions, bonusMultiplier, isExecutive, departmentCode, overrideFlag) {
  let gross = employee.baseSalary || 0;
  let net = 0;

  if (isExecutive) {
    if (departmentCode === 'EXEC_99') {
      if (bonusMultiplier > 2.0) {
        gross += 50000;
        if (overrideFlag) {
          gross += 10000;
        }
      } else {
        gross += 20000;
      }
    } else {
      gross += 10000;
    }
  } else {
    for (let i = 0; i < deductions.length; i++) {
      if (deductions[i].isActive) {
        if (deductions[i].type === 'HEALTH') {
          gross -= deductions[i].amount * 0.8;
        } else if (deductions[i].type === 'PENSION') {
          gross -= deductions[i].amount * 0.95;
        } else {
          gross -= deductions[i].amount;
        }
      }
    }
  }

  while (gross > 100000 && taxRate < 0.45) {
    if (departmentCode === 'SALES') {
      taxRate += 0.01;
    } else {
      taxRate += 0.02;
    }
  }

  try {
    net = gross * (1 - taxRate);
    if (net < 0) {
      net = 0;
    }
  } catch (err) {
    net = employee.baseSalary * 0.5;
  }

  return net;
}
