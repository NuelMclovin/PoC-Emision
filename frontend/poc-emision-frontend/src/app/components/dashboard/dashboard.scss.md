:host {
  display: block;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1rem;
}

.summary-card {
  background: #fff;
  border-radius: 22px;
  padding: 1.5rem;
  border: 1px solid rgba(19, 32, 58, 0.08);
  box-shadow: 0 18px 45px rgba(25, 34, 73, 0.08);
  border-top: 4px solid transparent;

  strong {
    display: block;
    font-size: 2.1rem;
    line-height: 1;
    margin: 0.4rem 0 0.55rem;
    color: #14108f;
  }

  small {
    color: #697792;
  }
}

.accent-red {
  border-top-color: #ff3a3a;
}

.accent-blue {
  border-top-color: #2b33bf;
}

.accent-gold {
  border-top-color: #f4a524;
}

.summary-label {
  color: #697792;
  font-size: 0.85rem;
  font-weight: 600;
}

.widgets-section,
.history-section {
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(19, 32, 58, 0.08);
  border-radius: 26px;
  padding: 1.5rem;
  box-shadow: 0 16px 38px rgba(25, 34, 73, 0.06);
}

.section-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.2rem;

  h2 {
    font-size: 1.35rem;
    color: #14108f;
    margin-bottom: 0.2rem;
  }

  p {
    color: #697792;
  }
}

.widget-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1.25rem;
}

.widget-card {
  background: #fff;
  border: 1px solid #dbe1f0;
  border-radius: 22px;
  padding: 1.35rem;
  display: grid;
  gap: 1rem;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;

  p {
    color: #697792;
  }

  &:hover {
    border-color: rgba(20, 16, 143, 0.24);
    box-shadow: 0 18px 38px rgba(20, 16, 143, 0.08);
    transform: translateY(-1px);
  }
}

.widget-card-compact {
  align-content: start;
  min-height: 220px;
}

.widget-head h3 {
  font-size: 1.35rem;
  color: #13203a;
}

.widget-kicker {
  display: inline-block;
  margin-bottom: 0.35rem;
  color: #2b33bf;
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-weight: 700;
}

.widget-link,
.primary-action,
.table-action {
  border: 0;
  cursor: pointer;
  font: inherit;
}

.widget-link-inline {
  padding: 0;
  background: transparent;
  color: #2148da;
  text-align: left;
  justify-self: start;
  font-weight: 700;
}

.history-heading {
  margin-bottom: 1rem;
}

.primary-action {
  min-height: 48px;
  border-radius: 14px;
  padding: 0.85rem 1.15rem;
  font-weight: 700;
  background: #ff3131;
  color: #fff;
}

.history-table-wrapper {
  overflow-x: auto;
}

.history-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 760px;

  th,
  td {
    padding: 1rem 0.85rem;
    text-align: left;
    border-bottom: 1px solid #edf1f7;
    font-size: 0.92rem;
  }

  th {
    color: #697792;
    font-weight: 700;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
}

.folio-cell {
  color: #2b33bf;
  font-weight: 700;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.35rem 0.7rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
  border: 1px solid transparent;

  &.en-proceso {
    color: #2f6fd0;
    background: rgba(47, 111, 208, 0.1);
    border-color: rgba(47, 111, 208, 0.2);
  }

  &.pendiente {
    color: #b97700;
    background: rgba(244, 165, 36, 0.12);
    border-color: rgba(244, 165, 36, 0.22);
  }

  &.en-revision {
    color: #7b45c5;
    background: rgba(123, 69, 197, 0.1);
    border-color: rgba(123, 69, 197, 0.18);
  }

  &.completado {
    color: #258d52;
    background: rgba(46, 170, 98, 0.1);
    border-color: rgba(46, 170, 98, 0.18);
  }
}

.table-action {
  padding: 0.45rem 0.85rem;
  border-radius: 10px;
  background: rgba(20, 16, 143, 0.08);
  color: #14108f;
  font-weight: 700;
}

@media (max-width: 1100px) {
  .summary-grid,
  .widget-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 820px) {
  .section-heading {
    flex-direction: column;
    align-items: stretch;
  }
}