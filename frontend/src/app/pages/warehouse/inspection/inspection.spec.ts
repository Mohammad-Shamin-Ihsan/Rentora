import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Inspection } from './inspection';

describe('Inspection', () => {
  let component: Inspection;
  let fixture: ComponentFixture<Inspection>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Inspection],
    }).compileComponents();

    fixture = TestBed.createComponent(Inspection);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
