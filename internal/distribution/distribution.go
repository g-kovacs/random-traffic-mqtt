package distribution

import (
	"math/rand"
)

type Distribution interface {
	next() int
}

type Exponential struct {
	Lambda float64
}

func (e Exponential) next() int {
	val := rand.ExpFloat64() / e.Lambda
	return int(val)
}

func NewExponential(lambda float64) *Exponential {
	return &Exponential{Lambda: lambda}
}

type Normal struct {
	Mu    float64
	Sigma float64
}

func (n Normal) next() int {
	val := rand.NormFloat64()*n.Sigma + n.Mu
	return int(val)
}

func NewNormal(mu, sigma float64) *Normal {
	return &Normal{Mu: mu, Sigma: sigma}
}
