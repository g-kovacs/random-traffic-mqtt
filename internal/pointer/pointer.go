package pointer

func SafeFloat64Ptr(p *float64) float64 {
	if p == nil {
		return 0.0
	}
	return *p
}
