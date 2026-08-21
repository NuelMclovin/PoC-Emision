import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Validacion } from './validacion';

describe('Validacion', () => {
  let component: Validacion;
  let fixture: ComponentFixture<Validacion>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Validacion],
    }).compileComponents();

    fixture = TestBed.createComponent(Validacion);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
