import { TestBed } from '@angular/core/testing';

import { Validacion } from './validacion';

describe('Validacion', () => {
  let service: Validacion;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(Validacion);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
