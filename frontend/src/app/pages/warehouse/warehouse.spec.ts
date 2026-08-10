import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Warehouse } from './warehouse';

describe('Warehouse', () => {
  let component: Warehouse;
  let fixture: ComponentFixture<Warehouse>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Warehouse],
    }).compileComponents();

    fixture = TestBed.createComponent(Warehouse);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
