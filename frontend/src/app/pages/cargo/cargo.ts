import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

interface Shipment {
  id:                              string;
  import_request_id:               string;
  status:                          string;
  tracking_notes:                  string | null;
  product_name:                    string;
  product_description:             string | null;
  estimated_budget:                number;
  preferred_rental_duration_days:  number;
  customer_name:                   string;
  customer_email:                  string;
  created_at:                      string;
  updated_at:                      string;
}

@Component({
  selector: 'app-cargo',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './cargo.html',
  styleUrls: ['./cargo.css']
})
export class Cargo implements OnInit {

  private apiUrl = environment.apiUrl;

  readonly stages = ['purchased', 'in_transit', 'customs_cleared', 'arrived'];

  shipments:     Shipment[] = [];
  isLoading      = true;
  accessDenied   = false;
  noteDrafts:    Record<string, string> = {};
  updatingId:    string | null = null;

  constructor(
    private http: HttpClient,
    private cdr:  ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.loadShipments();
  }

  loadShipments() {
    this.http.get<any>(`${this.apiUrl}/cargo/shipments`).subscribe({
      next: (res) => {
        this.shipments = res.data || [];
        this.isLoading  = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        if (err.status === 403) this.accessDenied = true;
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  stageIndex(status: string): number {
    return this.stages.indexOf(status);
  }

  nextStage(status: string): string | null {
    const i = this.stageIndex(status);
    return i >= 0 && i < this.stages.length - 1 ? this.stages[i + 1] : null;
  }

  stageLabel(stage: string): string {
    const map: Record<string, string> = {
      'purchased':       'Purchased',
      'in_transit':      'In Transit',
      'customs_cleared': 'Customs Cleared',
      'arrived':         'Arrived'
    };
    return map[stage] || stage;
  }

  advance(shipment: Shipment) {
    const next = this.nextStage(shipment.status);
    if (!next) return;

    this.updatingId = shipment.id;
    this.cdr.detectChanges();

    this.http.patch<any>(`${this.apiUrl}/cargo/shipments/${shipment.id}`, {
      status:         next,
      tracking_notes: this.noteDrafts[shipment.id] || null
    }).subscribe({
      next: (res) => {
        this.updatingId = null;
        delete this.noteDrafts[shipment.id];
        if (res.new_product) {
          alert(`"${res.new_product.title}" has been added to the rental catalog!`);
        }
        this.loadShipments();
        this.cdr.detectChanges();
      },
      error: (err) => {
        alert(err.error?.detail || 'Failed to update shipment.');
        this.updatingId = null;
        this.cdr.detectChanges();
      }
    });
  }

  formatPrice(price: number): string {
    return '৳' + Number(price).toLocaleString('en-BD');
  }

  formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric'
    });
  }
}
